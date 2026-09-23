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


def process_folder(
    input_path, output_csv="output_fast.csv", max_workers=None, skip_existing=True
):
    """Process all HTML files using multithreading and lxml for maximum speed."""
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

    # TESTING: Limit to first N files (comment out to process all)
    # files = files[:5]  # Process only first 5 files

    print(f"Found {len(files)} HTML files. Starting extraction...")

    # Skip already processed titles
    processed_titles = set()
    if skip_existing and os.path.exists(output_csv):
        with open(output_csv, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed_titles.add(row["title"])

    new_files = []
    for f in files:
        name = os.path.basename(f).replace(".html", "").strip()
        if name not in processed_titles:
            new_files.append(f)

    print(f"Processing {len(new_files)} new files...")

    # Use all CPU threads by default
    if max_workers is None:
        import multiprocessing

        max_workers = min(16, multiprocessing.cpu_count() * 2)

    all_dramas = []

    # Parallel execution
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(extract_mydramalist_data, f): f for f in new_files}
        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Extracting", unit="file"
        ):
            result = future.result()
            if result:
                all_dramas.append(result)

    # Save to CSV
    if all_dramas:
        write_mode = "a" if skip_existing and os.path.exists(output_csv) else "w"
        keys = list(all_dramas[0].keys())
        with open(output_csv, write_mode, encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            if write_mode == "w":
                writer.writeheader()
            writer.writerows(all_dramas)

        print(f"Extracted {len(all_dramas)} dramas and saved to '{output_csv}'")
    else:
        print("No new dramas extracted.")


if __name__ == "__main__":
    process_folder(
        r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\dramas_html",
        output_csv=r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\dramalist_all_dramas.csv",
        max_workers=None,
        skip_existing=True,
    )
