# code is 10x faster using lxml and multithreading
import json
import os
import csv
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from lxml import html

# Precompile regex
TVSERIES_RE = re.compile("TVSeries")
DESC_CLASS_RE = re.compile(
    r"(show-synopsis|show-synopsis__text|show-details-item__content)"
)


def extract_media_type(doc):
    """Extract the displayed media type, using the subtitle as a fallback."""
    type_nodes = doc.xpath(
        "//li[b[normalize-space()='Type:']]/span[1]/text()"
    )
    if type_nodes:
        media_type = type_nodes[0].strip()
        if media_type:
            return media_type

    subtitle_nodes = doc.xpath(
        "//div[contains(concat(' ', normalize-space(@class), ' '), "
        "' film-subtitle ')]//span[1]"
    )
    if subtitle_nodes:
        subtitle_parts = [
            part.strip() for part in subtitle_nodes[0].text_content().split("‧")
        ]
        if len(subtitle_parts) >= 2 and subtitle_parts[1]:
            return subtitle_parts[1]

    return None


def extract_mydramalist_data(file_path):
    """Ultra-fast extractor using lxml (no BeautifulSoup)."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        return None

    try:
        doc = html.fromstring(text)
    except Exception:
        return None

    # Extract JSON-LD data
    jsonld = None
    for elem in doc.xpath("//script[@type='application/ld+json']"):
        content = elem.text or ""
        if "TVSeries" in content:
            jsonld = content
            break

    data = {}
    if jsonld:
        try:
            data = json.loads(jsonld)
        except Exception:
            return None

    aggr = data.get("aggregateRating", {}) or {}
    drama_info = {
        "title": data.get("name"),
        "media_type": extract_media_type(doc),
        "alternate_names": (
            ", ".join(data["alternateName"])
            if isinstance(data.get("alternateName"), list)
            else data.get("alternateName")
        ),
        "url": data.get("url"),
        "description": data.get("description"),
        "image": data.get("image"),
        "publisher": (data.get("publisher") or {}).get("name"),
        "country": (data.get("countryOfOrigin") or {}).get("name"),
        "genres": (
            ", ".join(data["genre"])
            if isinstance(data.get("genre"), list)
            else data.get("genre")
        ),
        "rating_value": aggr.get("ratingValue"),
        "rating_count": aggr.get("ratingCount"),
        "date_published": data.get("datePublished"),
        "keywords": (
            ", ".join(data["keywords"])
            if isinstance(data.get("keywords"), list)
            else data.get("keywords")
        ),
        "actors": ", ".join(a.get("name", "") for a in data.get("actor", [])),
    }

    # Extract longer description if available
    desc_nodes = doc.xpath(
        "//div[contains(@class,'show-synopsis') or "
        "contains(@class,'show-synopsis__text') or "
        "contains(@class,'show-details-item__content')]"
    )
    if desc_nodes:
        full_desc = " ".join(desc_nodes[0].itertext()).strip()
        if full_desc and len(full_desc) > len(str(drama_info.get("description") or "")):
            drama_info["description"] = full_desc

    # Extract Directors
    directors = []
    director_elements = doc.xpath(
        "//li[contains(@class,'list-item')]//b[contains(@class,'inline') and contains(text(),'Director')]/following-sibling::a"
    )
    for elem in director_elements:
        director_name = elem.text_content().strip()
        if director_name:
            directors.append(director_name)
    drama_info["directors"] = ", ".join(directors) if directors else None

    # Extract Screenwriters
    screenwriters = []
    screenwriter_elements = doc.xpath(
        "//li[contains(@class,'list-item')]//b[contains(@class,'inline') and contains(text(),'Screenwriter')]/following-sibling::a"
    )
    for elem in screenwriter_elements:
        screenwriter_name = elem.text_content().strip()
        if screenwriter_name:
            screenwriters.append(screenwriter_name)
    drama_info["screenwriters"] = ", ".join(screenwriters) if screenwriters else None

    # Extract additional info fields: Country, Episodes, Aired, Score, Duration, Ranked, Watchers, Content Rating, Popularity
    wanted_fields = [
        "Country",
        "Episodes",
        "Aired",
        "Score",
        "Duration",
        "Ranked",
        "Watchers",
        "Content Rating",
        "Popularity",
    ]
    info_elements = doc.xpath(
        "//ul[contains(@class,'list') and contains(@class,'hidden-md-up')]//li"
    )

    for li in info_elements:
        key_elements = li.xpath(".//b[contains(@class,'inline')]")
        if key_elements:
            key = key_elements[0].text_content().strip().rstrip(":")
            if key in wanted_fields:
                # Get the full text and remove the key part
                full_text = li.text_content().strip()
                value = full_text.replace(key + ":", "").strip()
                # Map to lowercase with underscores for CSV column names
                field_name = key.lower().replace(" ", "_")
                drama_info[field_name] = value

    return drama_info


# Column order of the output CSV when it is created from scratch.
COLUMNS = [
    "title", "media_type", "alternate_names", "url", "description", "image", "publisher",
    "country", "genres", "rating_value", "rating_count", "date_published", "keywords",
    "actors", "directors", "screenwriters", "episodes", "aired", "duration", "score",
    "ranked", "popularity", "content_rating", "watchers",
]


def drama_id_of(value):
    """Drama ID from a URL or file path: '.../100-my-fair-lady(.html)' -> '100-my-fair-lady'."""
    name = str(value or "").strip().rstrip("/").replace("\\", "/").split("/")[-1]
    return name[:-5] if name.lower().endswith(".html") else name


def drama_key(value):
    """MyDramaList's permanent numeric ID ('100-my-fair-lady' -> '100'). The slug after it
    can change when a drama is renamed, so rows are keyed on the number."""
    drama_id = drama_id_of(value)
    number = drama_id.split("-", 1)[0]
    return number if number.isdigit() else drama_id


def process_folder(
    input_path, output_csv="output_fast.csv", max_workers=None, skip_existing=True, failed_list=None
):
    """Extract drama pages into `output_csv`, one row per MyDramaList ID (see drama_key).

    With skip_existing=True only pages not in the CSV yet, or saved after the CSV was last
    written (re-downloaded by Step 1), are extracted; their rows replace the old ones in
    place and new dramas are appended. skip_existing=False re-extracts everything. Pages
    that can't be parsed keep their old row (if any) and are listed in `failed_list` for
    Step 1 to re-download. If a drama was saved under two slugs, the newest file wins.
    """
    if not os.path.exists(input_path):
        print(f"Path not found: {input_path}")
        return

    # Collect HTML files
    if os.path.isdir(input_path):
        files = [
            os.path.join(input_path, f)
            for f in os.listdir(input_path)
            if f.lower().endswith(".html")
        ]
    else:
        files = [input_path]

    if not files:
        print("No HTML files found.")
        return

    print(f"Found {len(files)} HTML files.")

    # Existing rows by drama ID; rows without a URL are leftovers from failed parses.
    columns, rows, dropped = list(COLUMNS), {}, 0
    csv_mtime = 0.0
    if skip_existing and os.path.exists(output_csv):
        csv_mtime = os.path.getmtime(output_csv)
        with open(output_csv, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            columns = list(reader.fieldnames)
            for row in reader:
                if drama_id_of(row.get("url")):
                    rows[drama_key(row["url"])] = row
                else:
                    dropped += 1
    if dropped:
        print(f"Dropping {dropped} rows without a URL (failed parses from earlier runs).")

    newest = {}
    for f in files:
        key = drama_key(f)
        if key not in newest or os.path.getmtime(f) > os.path.getmtime(newest[key]):
            newest[key] = f
    new_files = [
        f for key, f in newest.items()
        if key not in rows or os.path.getmtime(f) > csv_mtime
    ]

    print(f"Processing {len(new_files)} new or re-downloaded files...")

    # Use all CPU threads by default
    if max_workers is None:
        import multiprocessing

        max_workers = min(16, multiprocessing.cpu_count() * 2)

    extracted, failed = {}, []

    # Parallel execution
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(extract_mydramalist_data, f): f for f in new_files}
        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Extracting", unit="file"
        ):
            drama_id = drama_id_of(futures[future])
            result = future.result()
            if result and result.get("title"):
                result["url"] = result.get("url") or f"https://mydramalist.com/{drama_id}"
                extracted[drama_key(drama_id)] = result
            else:
                failed.append(drama_id)

    updated = sum(1 for key in extracted if key in rows)
    rows.update(extracted)

    # Rewrite the whole CSV (via a temp file) so refreshed dramas replace their old row.
    temp_csv = output_csv + ".tmp"
    with open(temp_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows.values())
    os.replace(temp_csv, output_csv)

    if failed_list:
        with open(failed_list, "w", encoding="utf-8") as f:
            f.writelines(f"{drama_id}\n" for drama_id in sorted(failed))

    print(
        f"Extracted {len(extracted)} dramas ({len(extracted) - updated} new, {updated} updated), "
        f"{len(failed)} pages could not be parsed. {len(rows)} rows saved to '{output_csv}'"
    )


if __name__ == "__main__":
    process_folder(
        r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\dramas_html",
        output_csv=r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\dramalist_all_dramas.csv",
        max_workers=None,
        skip_existing=True,
        failed_list=r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\dramas_html_failed.txt",
    )
