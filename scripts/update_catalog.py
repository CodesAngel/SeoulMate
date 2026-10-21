"""One command that updates the drama catalog end to end.

Stages (each logged; any failure stops the run and, once the database or the live
index has changed, rolls back to the last good release):

  scrape          scrapers/DramaList_Scrapper/run_pipeline.py --refresh (new and due
                  dramas, validated publish into data/final, poster download)
  release-data    choose the release rows: the live release in its order, then new
                  dramas that have a poster (others wait for a later run); stop here
                  if nothing changed since the live release
  build           build FAISS + metadata into training/faiss_index.candidate/ with the
                  bi-encoder the backend loads
  validate        counts, dimension, row order vs CSV, live positions unchanged,
                  vectors finite and normalised, self-search
  catalog-check   scripts/import_catalog.py --dry-run against the candidate
  catalog-import  import into PostgreSQL                         (database changes)
  poster-audit    scripts/audit_poster_inventory.py
  thumbnails      scripts/generate_poster_thumbnails.py
  poster-upload   scripts/upload_posters_to_storage.py --skip-unchanged
  activate        faiss_index -> faiss_index.prev, candidate -> faiss_index
  ranking         backend/ranking/generate_indexes.py (only with --ranking-indexes)
  restart         --restart-cmd, then health check + test search (--health-url)

Without --restart-cmd the run ends with "restart_required": the backend keeps serving
the old index from memory until it is restarted by hand.

A lock file prevents overlapping runs. Each run writes logs/update/<run id>.log and
logs/update/status.json (timestamps in Asia/Karachi time). Exit code 0 = released or
nothing to do, 1 = failed (rolled back where needed), 2 = another run holds the lock.

Examples:
    python scripts/update_catalog.py --skip-scrape --no-db        # build + validate only
    python scripts/update_catalog.py --restart-cmd "sudo systemctl restart seoulmate-backend"
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pickle
import re
import shlex
import shutil
import subprocess
import sys
import time
import traceback
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRAPER_DIR = PROJECT_DIR / "scrapers" / "DramaList_Scrapper"
FINAL_CSV = PROJECT_DIR / "data" / "final" / "kdrama_dataset.csv"
PUBLISH_REPORT = PROJECT_DIR / "data" / "reports" / "dataset_publish_report.json"
POSTER_DIR = SCRAPER_DIR / "output" / "drama_image_by_id"
TRAINING_DIR = PROJECT_DIR / "training"
MODEL_DIR = TRAINING_DIR / "models"
LIVE_DIR = TRAINING_DIR / "faiss_index"
CANDIDATE_DIR = TRAINING_DIR / "faiss_index.candidate"
PREV_DIR = TRAINING_DIR / "faiss_index.prev"
LOG_DIR = PROJECT_DIR / "logs" / "update"
LOCK_FILE = LOG_DIR / "update.lock"
STATUS_FILE = LOG_DIR / "status.json"

# The release folder holds the dataset it was built from, so the database can always
# be re-imported to match the index (rollback) and the next run can tell what changed.
DATASET_NAME = "dataset.csv"
MANIFEST_NAME = "manifest.json"

POSTER_ID_PATTERN = re.compile(r"\[([^\[\]]+)\]\.[A-Za-z0-9]+$")
PKT = timezone(timedelta(hours=5), "PKT")


class StageError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Logging and status
# ---------------------------------------------------------------------------
class Run:
    def __init__(self, args):
        self.args = args
        self.run_id = datetime.now(PKT).strftime("%Y%m%d-%H%M%S")
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.log_path = LOG_DIR / f"{self.run_id}.log"
        self.log_file = self.log_path.open("a", encoding="utf-8")
        self.status = {
            "run_id": self.run_id,
            "started_at": now(),
            "finished_at": None,
            "result": "running",
            "stage": None,
            "stages": [],
            "log": str(self.log_path),
            "database_changed": False,
            "index_activated": False,
            "restart_required": False,
            "error": None,
        }
        self.save()

    def log(self, message=""):
        line = f"[{datetime.now(PKT).strftime('%H:%M:%S')}] {message}"
        print(line, flush=True)
        self.log_file.write(line + "\n")
        self.log_file.flush()

    def save(self):
        temp = STATUS_FILE.with_suffix(".tmp")
        temp.write_text(json.dumps(self.status, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, STATUS_FILE)

    def stage(self, name):
        return Stage(self, name)

    def command(self, args, cwd=PROJECT_DIR, allow_failure=False):
        """Run a command, copying its output to the console and the run log."""
        self.log(f"$ {' '.join(str(a) for a in args)}")
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
        process = subprocess.Popen(
            [str(a) for a in args],
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in process.stdout:
            line = line.rstrip()
            if line:
                print(f"    {line}", flush=True)
                self.log_file.write(f"    {line}\n")
        self.log_file.flush()
        code = process.wait()
        if code != 0 and not allow_failure:
            raise StageError(f"command failed with exit code {code}: {Path(str(args[1])).name}")
        return code

    def finish(self, result, error=None):
        self.status.update(result=result, error=error, finished_at=now(), stage=None)
        self.save()
        self.log(f"Result: {result}" + (f" ({error})" if error else ""))
        self.log_file.close()


class Stage:
    def __init__(self, run, name):
        self.run, self.name = run, name

    def __enter__(self):
        self.started = time.time()
        self.run.status["stage"] = self.name
        self.run.save()
        self.run.log(f"=== {self.name} ===")
        return self

    def __exit__(self, exc_type, exc, _tb):
        self.run.status["stages"].append(
            {
                "name": self.name,
                "ok": exc is None,
                "seconds": round(time.time() - self.started, 1),
            }
        )
        self.run.save()
        return False


def now():
    return datetime.now(PKT).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Lock
# ---------------------------------------------------------------------------
def acquire_lock():
    """Return True if this process now holds the lock. A lock left by a process that
    is no longer running is taken over."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"pid": os.getpid(), "started_at": now()})
    for _ in range(2):
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                holder = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                holder = {}
            if process_alive(holder.get("pid")):
                print(f"Another update is running (pid {holder.get('pid')}, since {holder.get('started_at')}).")
                return False
            print(f"Removing stale lock from pid {holder.get('pid')}.")
            LOCK_FILE.unlink(missing_ok=True)
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        return True
    return False


def process_alive(pid):
    if not pid:
        return False
    try:
        import psutil

        return psutil.pid_exists(int(pid))
    except ImportError:
        return True  # can't tell; never steal a lock we can't check


def release_lock():
    LOCK_FILE.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Dataset helpers
# ---------------------------------------------------------------------------
def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames), list(reader)


def write_rows(path, columns, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_id(url):
    return os.path.splitext(os.path.basename(urllib.parse.urlparse(str(url).strip()).path))[0]


def mdl_id(url):
    number = str(url or "").strip().rstrip("/").split("/")[-1].split("-", 1)[0]
    return number if number.isdigit() else ""


def identity(row):
    """Stable drama identity: MyDramaList ID, else poster image ID."""
    return f"mdl:{mdl_id(row.get('url'))}" if mdl_id(row.get("url")) else f"img:{image_id(row['image'])}"


def join_key(title, aired):
    clean = lambda value: re.sub(r"\s+", " ", str(value or "")).strip().casefold()
    return clean(title), clean(aired)


def poster_ids():
    return {
        match.group(1)
        for path in POSTER_DIR.iterdir()
        if path.is_file() and (match := POSTER_ID_PATTERN.search(path.name))
    }


def backend_model_dir():
    """The bi-encoder the backend loads: the first model folder (sorted) with a
    config.json whose name doesn't contain "cross" (see backend/app.py, Stage 1)."""
    names = sorted(
        name
        for name in os.listdir(MODEL_DIR)
        if not name.startswith(".") and (MODEL_DIR / name / "config.json").is_file()
    )
    bi_encoders = [name for name in names if "cross" not in name.lower()]
    if not bi_encoders:
        raise StageError(f"No bi-encoder model folder in {MODEL_DIR}")
    return MODEL_DIR / bi_encoders[0]


def ensure_live_snapshot(run):
    """Make sure the live release folder holds the dataset its index was built from.
    For an index built before this script existed, data/final is used if it matches
    the live metadata row for row; otherwise rollback of the database is unavailable."""
    if (LIVE_DIR / DATASET_NAME).exists():
        return True
    if not (LIVE_DIR / "meta.pkl").exists():
        run.log("No live index yet.")
        return False
    with (LIVE_DIR / "meta.pkl").open("rb") as handle:
        metadata = pickle.load(handle)
    columns, rows = read_rows(FINAL_CSV)
    live_keys = [join_key(m.get("Title"), m.get("Release Years")) for m in metadata]
    final_keys = [join_key(r.get("title"), r.get("aired")) for r in rows]
    if live_keys != final_keys:
        run.log("Warning: live index doesn't match data/final row for row; database rollback unavailable for this run.")
        return False
    write_rows(LIVE_DIR / DATASET_NAME, columns, rows)
    run.log(f"Saved {len(rows)}-row snapshot of the live dataset to {LIVE_DIR / DATASET_NAME}.")
    return True


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------
def stage_scrape(run):
    args = [sys.executable, "run_pipeline.py", "--refresh"]
    if run.args.max_pages is not None:
        args += ["--max-pages", run.args.max_pages]
    if run.args.max_fetch is not None:
        args += ["--max-fetch", run.args.max_fetch]
    run.command(args, cwd=SCRAPER_DIR)
    if PUBLISH_REPORT.exists():
        report = json.loads(PUBLISH_REPORT.read_text(encoding="utf-8"))
        run.status["publish"] = {
            key: report.get(key)
            for key in ("published", "new_count", "updated_count", "embedding_text_changed", "errors")
        }
        run.status["publish"]["poster_held_back"] = len(report.get("poster_held_back", []))


def stage_release_data(run):
    """Write the candidate dataset and return True if it differs from the live one."""
    columns, final_rows = read_rows(FINAL_CSV)
    posters = poster_ids()

    live_rows = []
    if (LIVE_DIR / DATASET_NAME).exists():
        _, live_rows = read_rows(LIVE_DIR / DATASET_NAME)
    final_by_identity = {identity(row): row for row in final_rows}
    live_identities = {identity(row) for row in live_rows}

    # Live dramas keep their positions (the database's catalog_index); their values
    # come from data/final. New dramas follow, if their poster has been downloaded.
    release, missing_live = [], []
    for row in live_rows:
        current = final_by_identity.get(identity(row))
        if current is None:
            missing_live.append(row["title"])
            current = row
        release.append({column: current.get(column, "") for column in columns})
    deferred = []
    for row in final_rows:
        if identity(row) in live_identities:
            continue
        if image_id(row["image"]) in posters:
            release.append(row)
        else:
            deferred.append(row["title"])

    for row in release:
        if image_id(row["image"]) not in posters:
            raise StageError(f"Live drama has no local poster: {row['title']!r} ({image_id(row['image'])})")
    if missing_live:
        run.log(f"Warning: {len(missing_live)} live dramas are missing from data/final and were kept: {missing_live[:5]}")
    if deferred:
        run.log(f"{len(deferred)} new dramas wait for their poster: {deferred[:10]}")
    run.status["release"] = {
        "rows": len(release),
        "live_rows": len(live_rows),
        "new_rows": len(release) - len(live_rows),
        "deferred_no_poster": deferred,
    }

    if CANDIDATE_DIR.exists():
        shutil.rmtree(CANDIDATE_DIR)
    CANDIDATE_DIR.mkdir(parents=True)
    write_rows(CANDIDATE_DIR / DATASET_NAME, columns, release)

    if not (LIVE_DIR / DATASET_NAME).exists():
        run.log("Live release has no dataset snapshot; a full release is needed.")
        return True
    changed = sha256_file(CANDIDATE_DIR / DATASET_NAME) != sha256_file(LIVE_DIR / DATASET_NAME)
    run.log(f"Release dataset: {len(release)} rows ({len(release) - len(live_rows)} new); "
            f"{'changed' if changed else 'identical to the live release'}.")
    return changed


def stage_build(run, model_dir):
    run.command(
        [
            sys.executable,
            TRAINING_DIR / "steps" / "step3_build_index.py",
            "--data", CANDIDATE_DIR / DATASET_NAME,
            "--out-dir", CANDIDATE_DIR,
            "--model", model_dir,
        ],
        cwd=TRAINING_DIR,
    )


def stage_validate(run, model_dir):
    import faiss
    import numpy as np

    index = faiss.read_index(str(CANDIDATE_DIR / "index.faiss"))
    with (CANDIDATE_DIR / "meta.pkl").open("rb") as handle:
        metadata = pickle.load(handle)
    _, rows = read_rows(CANDIDATE_DIR / DATASET_NAME)
    info = json.loads((CANDIDATE_DIR / "build_info.json").read_text(encoding="utf-8"))

    errors = []
    if not (index.ntotal == len(metadata) == len(rows) == info["rows"]):
        errors.append(f"row counts differ: index {index.ntotal}, meta {len(metadata)}, csv {len(rows)}")
    if Path(info["model"]).resolve() != Path(model_dir).resolve():
        errors.append(f"built with {info['model']}, backend loads {model_dir}")
    if info["dimension"] != index.d:
        errors.append(f"index dimension {index.d} doesn't match the build ({info['dimension']})")
    if info["data_sha256"] != sha256_file(CANDIDATE_DIR / DATASET_NAME):
        errors.append("index was built from a different dataset file")

    meta_keys = [join_key(m.get("Title"), m.get("Release Years")) for m in metadata]
    csv_keys = [join_key(r.get("title"), r.get("aired")) for r in rows]
    if meta_keys != csv_keys:
        first = next(i for i, (a, b) in enumerate(zip(meta_keys, csv_keys)) if a != b) if len(meta_keys) == len(csv_keys) else "count"
        errors.append(f"metadata order differs from the CSV (first at {first})")
    if len(set(csv_keys)) != len(csv_keys):
        errors.append("duplicate (title, aired) rows; scripts/import_catalog.py needs them unique")

    if (LIVE_DIR / DATASET_NAME).exists():
        _, live_rows = read_rows(LIVE_DIR / DATASET_NAME)
        moved = [r["title"] for i, r in enumerate(live_rows) if i >= len(rows) or identity(rows[i]) != identity(r)]
        if moved:
            errors.append(f"{len(moved)} live dramas changed position, e.g. {moved[:3]}")

    vectors = index.reconstruct_n(0, index.ntotal)
    norms = np.linalg.norm(vectors, axis=1)
    if not np.isfinite(vectors).all() or np.abs(norms - 1).max() > 1e-3:
        errors.append("vectors are not finite unit vectors")
    sample = np.linspace(0, index.ntotal - 1, num=min(25, index.ntotal), dtype=int)
    _, found = index.search(vectors[sample], 1)
    if not all(found[i][0] == position for i, position in enumerate(sample)):
        errors.append("self-search check failed")

    if errors:
        raise StageError("candidate index failed validation: " + "; ".join(errors))
    run.log(f"Candidate OK: {index.ntotal} dramas, dimension {index.d}, model {Path(model_dir).name}.")


def import_catalog_command(csv_path, meta_path, *extra):
    return [
        sys.executable, PROJECT_DIR / "scripts" / "import_catalog.py",
        "--csv", csv_path, "--meta", meta_path, "--posters", POSTER_DIR, *extra,
    ]


def stage_activate(run, model_dir):
    if PREV_DIR.exists():
        shutil.rmtree(PREV_DIR)
    if LIVE_DIR.exists():
        os.replace(LIVE_DIR, PREV_DIR)
    os.replace(CANDIDATE_DIR, LIVE_DIR)
    run.status["index_activated"] = True
    manifest = {
        "run_id": run.run_id,
        "activated_at": now(),
        "rows": run.status["release"]["rows"],
        "dataset_sha256": sha256_file(LIVE_DIR / DATASET_NAME),
        "model": str(Path(model_dir).relative_to(PROJECT_DIR)),
    }
    (LIVE_DIR / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    run.log(f"Activated: {LIVE_DIR} (previous release kept in {PREV_DIR}).")


def restart_and_check(run):
    run.command(shlex.split(run.args.restart_cmd, posix=os.name != "nt"), allow_failure=False)
    base = run.args.health_url.rstrip("/")
    deadline = time.time() + run.args.health_timeout
    while True:
        try:
            with urllib.request.urlopen(base + "/", timeout=10) as response:
                if response.status == 200:
                    break
        except OSError:
            pass
        if time.time() > deadline:
            raise StageError(f"backend did not answer {base}/ within {run.args.health_timeout}s")
        time.sleep(5)
    _, rows = read_rows(LIVE_DIR / DATASET_NAME)
    title = rows[-1]["title"]
    query = urllib.parse.urlencode({"title": title, "top_n": 3})
    with urllib.request.urlopen(f"{base}/recommend?{query}", timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload.get("recommendations"):
        raise StageError(f"test search for {title!r} returned no recommendations")
    run.log(f"Backend healthy; test search for {title!r} returned {len(payload['recommendations'])} results.")


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------
def rollback(run, can_restore_db):
    run.log("=== rollback ===")
    if run.status["index_activated"] and PREV_DIR.exists():
        failed = TRAINING_DIR / f"faiss_index.failed-{run.run_id}"
        os.replace(LIVE_DIR, failed)
        os.replace(PREV_DIR, LIVE_DIR)
        run.status["index_activated"] = False
        run.log(f"Restored the previous index; the failed one is in {failed}.")
    if run.status["database_changed"]:
        if not can_restore_db:
            run.log("Database can't be restored automatically (no live dataset snapshot). "
                    "The backend will refuse to restart until the catalog matches the index.")
            return False
        run.command(import_catalog_command(
            LIVE_DIR / DATASET_NAME, LIVE_DIR / "meta.pkl", "--prune", "--allow-extra-posters"
        ))
        run.status["database_changed"] = False
        run.log("Database catalog restored to the live release.")
    if run.args.restart_cmd and run.status.get("restarted"):
        restart_and_check(run)
    run.status["rolled_back"] = True
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def update(run):
    args = run.args
    can_restore_db = ensure_live_snapshot(run)
    model_dir = backend_model_dir()

    if not args.skip_scrape:
        with run.stage("scrape"):
            stage_scrape(run)

    with run.stage("release-data"):
        changed = stage_release_data(run)
    if not changed and not args.force:
        shutil.rmtree(CANDIDATE_DIR, ignore_errors=True)
        return "no_changes"

    with run.stage("build"):
        stage_build(run, model_dir)
    with run.stage("validate"):
        stage_validate(run, model_dir)
    with run.stage("catalog-check"):
        run.command(import_catalog_command(CANDIDATE_DIR / DATASET_NAME, CANDIDATE_DIR / "meta.pkl", "--dry-run"))
    if args.no_db:
        run.log(f"--no-db: stopping before the database. Candidate kept in {CANDIDATE_DIR}.")
        return "built"

    try:
        with run.stage("catalog-import"):
            run.status["database_changed"] = True
            run.command(import_catalog_command(CANDIDATE_DIR / DATASET_NAME, CANDIDATE_DIR / "meta.pkl"))
        with run.stage("poster-audit"):
            run.command([sys.executable, PROJECT_DIR / "scripts" / "audit_poster_inventory.py"])
        with run.stage("thumbnails"):
            run.command([sys.executable, PROJECT_DIR / "scripts" / "generate_poster_thumbnails.py"])
        with run.stage("poster-upload"):
            run.command([
                sys.executable, PROJECT_DIR / "scripts" / "upload_posters_to_storage.py",
                "--skip-unchanged", "--ignore-unexpected",
            ])
        with run.stage("activate"):
            stage_activate(run, model_dir)
        if args.ranking_indexes:
            with run.stage("ranking"):
                run.command([sys.executable, PROJECT_DIR / "backend" / "ranking" / "generate_indexes.py"])
        if args.restart_cmd:
            with run.stage("restart"):
                run.status["restarted"] = True
                restart_and_check(run)
        else:
            run.status["restart_required"] = True
            run.log("Restart the backend to serve the new release (no --restart-cmd given).")
    except Exception:
        try:
            rollback(run, can_restore_db)
        except Exception as error:  # report both; the original error comes first
            run.log(f"Rollback failed: {error}")
            run.status["rollback_error"] = str(error)
        raise
    return "released"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-scrape", action="store_true", help="use the current data/final, don't run the scraper")
    parser.add_argument("--max-pages", type=int, help="scraper: listing pages per source (default 5)")
    parser.add_argument("--max-fetch", type=int, help="scraper: drama pages per run (default 300)")
    parser.add_argument("--force", action="store_true", help="release even if the dataset is unchanged")
    parser.add_argument("--no-db", action="store_true", help="stop after building and checking the candidate")
    parser.add_argument("--ranking-indexes", action="store_true",
                        help="also regenerate backend/ranking/indexes/ (changes ranking; re-run the evaluation)")
    parser.add_argument("--restart-cmd", help="command that restarts the backend, e.g. \"sudo systemctl restart seoulmate-backend\"")
    parser.add_argument("--health-url", default="http://127.0.0.1:8001", help="backend base URL for the health check")
    parser.add_argument("--health-timeout", type=int, default=300, help="seconds to wait for the backend after a restart")
    return parser.parse_args()


def main():
    args = parse_args()
    if not acquire_lock():
        sys.exit(2)
    run = None
    try:
        run = Run(args)
        result = update(run)
        run.finish(result)
        code = 0
    except Exception as error:
        if run is None:
            raise
        run.log(traceback.format_exc().rstrip())
        run.finish("rolled_back" if run.status.get("rolled_back") else "failed", error=str(error))
        code = 1
    finally:
        release_lock()
    sys.exit(code)


if __name__ == "__main__":
    main()
