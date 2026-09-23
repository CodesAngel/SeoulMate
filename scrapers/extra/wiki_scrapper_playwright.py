from playwright.sync_api import sync_playwright
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time

# =========================================================
# Cleaning Helpers
# =========================================================
def remove_refs(text):
    """Remove all reference markers like [1], [ko], [citation needed]."""
    return re.sub(r'\[.*?\]', '', str(text))

def clean_multiline(text):
    """Convert multiline text to properly comma-separated clean string."""
    if not text or str(text).strip().lower() in ["n/a", "na"]:
        return "-"
    text = remove_refs(text)
    parts = re.split(r'[\n\r]+', str(text))
    parts = [p.strip() for p in parts if p.strip()]
    return ", ".join(parts) if parts else "-"

def clean_description(desc):
    """Clean [1], etc. and normalize spaces."""
    if not desc:
        return "-"
    desc = remove_refs(desc)
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc if desc else "-"

def extract_years_from_release(text):
    """Extract release year(s) from release date text."""
    if not text or str(text).strip().lower() in ["n/a", "na", "-"]:
        return "-"
    text = remove_refs(text)
    full_years = re.findall(r'(?:19|20)\d{2}', text)
    unique_years = list(dict.fromkeys(full_years))  # preserve order
    return ", ".join(unique_years) if unique_years else "-"

# =========================================================
# Fallback: Description method
# =========================================================
def get_description_fallback(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for heading_text in ["Synopsis", "Plot", "Premise", "Story", "Summary"]:
            heading = soup.find(["h2", "h3"], id=heading_text)
            if heading:
                p = heading.find_next("p")
                if p and p.get_text(strip=True):
                    return clean_description(p.get_text(strip=True))
        first_p = soup.find("p")
        if first_p:
            return clean_description(first_p.get_text(strip=True))
    except Exception as e:
        print(f"Fallback failed for {url}: {e}")
    return "-"

# =========================================================
# Main Scraper (Playwright)
# =========================================================
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # ---------------------------
    # Wikipedia main list
    # ---------------------------
    base_url = "https://en.wikipedia.org/wiki/List_of_South_Korean_dramas"
    print("Loading main page...")
    page.goto(base_url, timeout=60000)
    page.wait_for_selector(".div-col")

    # ---------------------------
    # Collect drama links
    # ---------------------------
    print("Collecting drama links...")
    drama_links = []
    divs = page.query_selector_all(".div-col")

    for div in divs:
        links = div.query_selector_all("a[href]")
        for link in links:
            href = link.get_attribute("href")
            if href and "wiki" in href and "redlink" not in href:
                if not href.startswith("http"):
                    href = "https://en.wikipedia.org" + href
                drama_links.append(href)

    drama_links = list(set(drama_links))
    print(f"✅ Found {len(drama_links)} drama links")

    # ---------------------------
    # Scrape each drama page
    # ---------------------------
    titles, alt_titles, writers, directors, casts, genres, networks = [], [], [], [], [], [], []
    episodes, releases, release_years, posters, descriptions = [], [], [], [], []

    for i, url in enumerate(drama_links):  # limit e.g. drama_links[:10]
        print(f"\n📄 Scraping ({i+1}/{len(drama_links)}): {url}")
        try:
            page.goto(url, timeout=60000)
            page.wait_for_selector("#firstHeading", timeout=10000)
        except:
            print(f"❌ Failed to load {url}")
            continue

        # ---------- Title ----------
        try:
            title = page.query_selector("#firstHeading").inner_text().strip()
        except:
            title = "-"

        # ---------- Defaults ----------
        alt_title = writer = director = cast = genre = network = episode = release = poster = desc = "-"

        # ---------- Infobox ----------
        try:
            infobox = page.query_selector(".infobox")
            if infobox:
                rows = infobox.query_selector_all("tr")
                for row in rows:
                    header_el = row.query_selector("th")
                    data_el = row.query_selector("td")
                    if not header_el or not data_el:
                        continue
                    header = header_el.inner_text().lower().strip()
                    data_text = data_el.inner_text().strip()

                    if "also known as" in header:
                        alt_title = data_text
                    elif "written by" in header:
                        writer = data_text
                    elif "directed by" in header:
                        director = data_text
                    elif "starring" in header:
                        cast = data_text
                    elif "genre" in header:
                        genre = data_text
                    elif "network" in header:
                        network = data_text
                    elif "episode" in header:
                        episode = data_text
                    elif "release" in header:
                        release = data_text

                    # Poster
                    img_el = data_el.query_selector("img")
                    if img_el:
                        poster = img_el.get_attribute("src")
                        if poster and poster.startswith("//"):
                            poster = "https:" + poster
        except Exception as e:
            print(f"Infobox error on {url}: {e}")

        # ---------- Description ----------
        try:
            heading_candidates = ["Synopsis", "Plot", "Premise", "Story"]
            desc_found = False
            for heading_text in heading_candidates:
                heading = page.query_selector(f"h2 span#{heading_text}, h2:has-text('{heading_text}')")
                if heading:
                    next_p = heading.evaluate_handle("el => el.parentElement.nextElementSibling")
                    if next_p:
                        desc_text = next_p.as_element().inner_text().strip()
                        desc = clean_description(desc_text)
                        desc_found = True
                        break
            if not desc_found:
                first_p = page.query_selector("p")
                if first_p:
                    desc = clean_description(first_p.inner_text().strip())
        except:
            pass

        # ---------- Fallback ----------
        if (not desc) or len(desc) < 50:
            print("⚠️ Using fallback description...")
            desc = get_description_fallback(url)

        # ---------- Clean & Extract ----------
        titles.append(title)
        alt_titles.append(clean_multiline(alt_title))
        writers.append(clean_multiline(writer))
        directors.append(clean_multiline(director))
        casts.append(clean_multiline(cast))
        genres.append(clean_multiline(genre))
        networks.append(remove_refs(network).strip() or "-")
        episodes.append(remove_refs(episode).strip() or "-")
        releases.append(remove_refs(release).strip() or "-")
        release_years.append(extract_years_from_release(release))
        posters.append(poster.strip() if poster else "-")
        descriptions.append(desc)

        time.sleep(0.3)  # light delay to avoid blocking

    # ---------------------------
    # Save as CSV
    # ---------------------------
    df = pd.DataFrame({
        "Title": titles,
        "Also Known As": alt_titles,
        "Written By": writers,
        "Director": directors,
        "Cast": casts,
        "Genre": genres,
        "Network": networks,
        "Episodes": episodes,
        "Release Dates": releases,
        "Release Years": release_years,
        "Poster": posters,
        "Description": descriptions
    })

    df.replace(["N/A", "NA", "", None], "-", inplace=True)
    df.to_csv("kdrama_dataset_detailed_v8_playwright.csv", index=False, encoding="utf-8-sig")

    print("\n✅ Done! Data saved to data_scrapper/kdrama_dataset_detailed_v8_playwright.csv")
    browser.close()
