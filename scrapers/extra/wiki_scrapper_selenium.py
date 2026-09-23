# import requests
# from bs4 import BeautifulSoup
# import pandas as pd
# from tqdm import tqdm
# import time

# # =========================================
# # CONFIG
# # =========================================
# BASE_URL = "https://mydramalist.com/shows/popular?page="
# NUM_PAGES = 1  # you can increase to scrape more pages
# HEADERS = {"User-Agent": "Mozilla/5.0"}  # prevent blocking

# # =========================================
# # SCRAPE LOGIC
# # =========================================
# all_dramas = []

# for page in tqdm(range(1, NUM_PAGES + 1), desc="Scraping pages"):
#     url = BASE_URL + str(page)
#     response = requests.get(url, headers=HEADERS)
#     soup = BeautifulSoup(response.text, "lxml")

#     boxes = soup.select(".box")  # each drama item

#     for box in boxes:
#         try:
#             # Title and link
#             title_tag = box.select_one(".text-primary.title a")
#             title = title_tag.text.strip()
#             drama_link = "https://mydramalist.com" + title_tag["href"]

#             # Image URL
#             img_tag = box.select_one(".film-cover img")
#             image_url = img_tag["src"] if img_tag else None

#             # Year and Episodes
#             info_text = box.select_one(".content span.text-muted")
#             year, episodes = None, None
#             if info_text:
#                 text = info_text.get_text(strip=True)
#                 # Example: "Korean Drama - 2016, 16 episodes"
#                 parts = text.split("-")[-1].split(",")
#                 if len(parts) == 2:
#                     year = parts[0].strip()
#                     episodes = parts[1].strip()
#                 else:
#                     year = parts[0].strip()

#             # Rating
#             rating_tag = box.select_one(".score")
#             rating = rating_tag.text.strip() if rating_tag else None

#             # Description
#             desc_tag = box.select_one(".content p:nth-of-type(2)")
#             description = desc_tag.get_text(strip=True) if desc_tag else None

#             all_dramas.append({
#                 "Title": title,
#                 "Year": year,
#                 "Episodes": episodes,
#                 "Rating": rating,
#                 "Description": description,
#                 "Image_URL": image_url,
#                 "Drama_Link": drama_link
#             })

#         except Exception as e:
#             print(f"⚠️ Error parsing box: {e}")
#             continue

#     time.sleep(1)  # be nice to the server

# # =========================================
# # SAVE TO CSV
# # =========================================
# df = pd.DataFrame(all_dramas)
# df.to_csv("kdrama_mydramalist.csv", index=False, encoding="utf-8-sig")

# print(f"\n Scraped {len(df)} dramas and saved to kdrama_mydramalist.csv")


# import requests
# import pandas as pd
# from bs4 import BeautifulSoup
# import time

# # Step 1: Target Wikipedia page
# urls = [
#     "https://en.wikipedia.org/wiki/List_of_Korean_dramas",
#     "https://en.wikipedia.org/wiki/List_of_South_Korean_television_series"
# ]


# # Step 2: Add headers to avoid 403 Forbidden
# headers = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                   "AppleWebKit/537.36 (KHTML, like Gecko) "
#                   "Chrome/120.0.0.0 Safari/537.36"
# }

# # Step 3: Fetch the page safely
# for url in urls:
#     response = requests.get(url, headers=headers)
#     response.raise_for_status()

# # Step 4: Parse the HTML
# soup = BeautifulSoup(response.text, "html.parser")

# # Step 5: Extract all tables on the page
# tables = soup.find_all("table", {"class": "wikitable"})

# dramas = []

# for table in tables:
#     df = pd.read_html(str(table))[0]

#     # Normalize column names
#     df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

#     # Common columns across tables
#     if "title" in df.columns:
#         for _, row in df.iterrows():
#             title = str(row.get("title", "")).strip()

#             # Extract link to get drama description later
#             link_tag = table.find("a", string=lambda s: s and s in title)
#             link = "https://en.wikipedia.org" + link_tag["href"] if link_tag else None

#             dramas.append({
#                 "title": title,
#                 "network": row.get("network", ""),
#                 "release_year": row.get("year", ""),
#                 "episodes": row.get("episodes", ""),
#                 "genre": row.get("genre", ""),
#                 "notes": row.get("notes", ""),
#                 "wiki_link": link
#             })

# # Step 6: Optional — fetch short descriptions from each Wikipedia page
# for drama in dramas[:30]:  # limit to 30 to avoid being blocked
#     if not drama["wiki_link"]:
#         continue
#     try:
#         sub_page = requests.get(drama["wiki_link"], headers=headers)
#         sub_soup = BeautifulSoup(sub_page.text, "html.parser")
#         p_tag = sub_soup.find("p")
#         drama["description"] = p_tag.text.strip() if p_tag else ""
#         time.sleep(1.5)  # be polite to Wikipedia
#     except Exception as e:
#         drama["description"] = ""
#         print(f"Failed for {drama['title']}: {e}")

# # Step 7: Save to CSV
# df_final = pd.DataFrame(dramas)
# df_final.to_csv("kdramas_2020s.csv", index=False, encoding="utf-8-sig")

# print(f" Saved {len(df_final)} dramas with details to kdramas_2020s.csv")




# # ====================================================
# # 📺 K-Drama Wikipedia Scraper (Enhanced v4) Working
# # ====================================================
# # Extracts:
# # - Title, Also known as, Written by, Directed by, Cast, Genre,
# #   Network, Episodes, Release date, Poster image, Description
# # Adds: fallback BeautifulSoup-based description if Selenium fails
# # ====================================================

# import requests
# from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.options import Options
# import pandas as pd
# import time

# # ---------------------------
# # Fallback: Description method
# # ---------------------------
# def get_description_fallback(url):
#     headers = {
#         "User-Agent": (
#             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#             "AppleWebKit/537.36 (KHTML, like Gecko) "
#             "Chrome/118.0.0.0 Safari/537.36"
#         )
#     }

#     try:
#         response = requests.get(url, headers=headers, timeout=10)
#         response.raise_for_status()
#         soup = BeautifulSoup(response.text, "html.parser")

#         # Search for section headings
#         for heading_text in ["Synopsis", "Plot", "Premise", "Story", "Summary"]:
#             heading = soup.find(["h2", "h3"], id=heading_text)
#             if heading:
#                 p = heading.find_next("p")
#                 if p and p.get_text(strip=True):
#                     return p.get_text(strip=True)

#         # Fallback to first paragraph
#         first_p = soup.find("p")
#         if first_p:
#             return first_p.get_text(strip=True)
#     except Exception as e:
#         print(f"Fallback failed for {url}: {e}")
#     return "No Description"


# # ---------------------------
# # Setup Selenium WebDriver
# # ---------------------------
# chrome_options = Options()
# chrome_options.add_argument("--headless")
# chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--disable-dev-shm-usage")

# driver = webdriver.Chrome(options=chrome_options)

# # ---------------------------
# # Wikipedia main list
# # ---------------------------
# base_url = "https://en.wikipedia.org/wiki/List_of_South_Korean_dramas"
# driver.get(base_url)
# time.sleep(3)

# # ---------------------------
# # Collect all drama links
# # ---------------------------
# print("Collecting drama links...")
# drama_links = []
# elems = driver.find_elements(By.CLASS_NAME, "div-col")

# for elem in elems:
#     links = elem.find_elements(By.CSS_SELECTOR, "a[href]")
#     for link in links:
#         href = link.get_attribute("href")
#         if href and "wiki" in href and "redlink" not in href:
#             drama_links.append(href)

# drama_links = list(set(drama_links))
# print(f"Found {len(drama_links)} drama links")

# # ---------------------------
# # Scrape each drama page
# # ---------------------------
# titles, alt_titles, writers, directors, casts, genres, networks, episodes, releases, posters, descriptions = [], [], [], [], [], [], [], [], [], [], []

# for i, url in enumerate(drama_links):  # limit to 10 for testing
#     print(f"\nScraping ({i+1}/{len(drama_links)}): {url}")
#     driver.get(url)
#     time.sleep(1.5)

#     # ---------- Title ----------
#     try:
#         title = driver.find_element(By.ID, "firstHeading").text.strip()
#     except:
#         title = "No Title"

#     # ---------- Defaults ----------
#     alt_title = writer = director = cast = genre = network = episode = release = poster = "N/A"
#     desc = "No Description"

#     # ---------- Infobox ----------
#     try:
#         infobox = driver.find_element(By.CLASS_NAME, "infobox")
#         rows = infobox.find_elements(By.TAG_NAME, "tr")

#         for row in rows:
#             try:
#                 header = row.find_element(By.TAG_NAME, "th").text.lower()
#                 data = row.find_element(By.TAG_NAME, "td")
#             except:
#                 continue

#             if "also known as" in header:
#                 alt_title = data.text
#             elif "written by" in header:
#                 writer = data.text
#             elif "directed by" in header:
#                 director = data.text
#             elif "starring" in header:
#                 cast = data.text
#             elif "genre" in header:
#                 genre = data.text
#             elif "network" in header:
#                 network = data.text
#             elif "episode" in header:
#                 episode = data.text
#             elif "release" in header:
#                 release = data.text

#             # Poster image
#             try:
#                 if "image" in data.get_attribute("class"):
#                     img = data.find_element(By.TAG_NAME, "img")
#                     poster = img.get_attribute("src")
#                     if poster.startswith("//"):
#                         poster = "https:" + poster
#             except:
#                 continue
#     except:
#         pass

#     # ---------- Description ----------
#     try:
#         heading_candidates = ["Synopsis", "Plot", "Premise", "Story"]
#         found_section = None

#         for heading_text in heading_candidates:
#             try:
#                 heading = driver.find_element(
#                     By.XPATH,
#                     f"//h2[.//span[@id='{heading_text}'] or contains(., '{heading_text}')]"
#                 )
#                 found_section = heading
#                 break
#             except:
#                 continue

#         if found_section:
#             next_p = found_section.find_element(By.XPATH, "following-sibling::p")
#             desc = next_p.text.strip()
#         else:
#             desc = driver.find_element(By.CSS_SELECTOR, "p").text.strip()
#     except:
#         pass

#     # ---------- Fallback check ----------
#     if (not desc) or len(desc) < 50 or desc.lower().startswith("no description"):
#         print("Using fallback description...")
#         desc = get_description_fallback(url)

#     # ---------- Append ----------
#     titles.append(title)
#     alt_titles.append(alt_title)
#     writers.append(writer)
#     directors.append(director)
#     casts.append(cast)
#     genres.append(genre)
#     networks.append(network)
#     episodes.append(episode)
#     releases.append(release)
#     posters.append(poster)
#     descriptions.append(desc)

# # ---------------------------
# # Save as CSV
# # ---------------------------
# df = pd.DataFrame({
#     "Title": titles,
#     "Also Known As": alt_titles,
#     "Written By": writers,
#     "Director": directors,
#     "Cast": casts,
#     "Genre": genres,
#     "Network": networks,
#     "Episodes": episodes,
#     "Release Dates": releases,
#     "Poster": posters,
#     "Description": descriptions
# })

# df.to_csv("kdrama_dataset_detailed_v4.csv", index=False, encoding="utf-8-sig")
# print("\nDone! Data saved to kdrama_dataset_detailed_v4.csv")

# driver.quit()



# # ====================================================
# # 📺 K-Drama Wikipedia Scraper (Enhanced v5 — Cleaned)
# # ====================================================
# # Extracts:
# # - Title, Also known as, Written by, Directed by, Cast, Genre,
# #   Network, Episodes, Release date, Poster image, Description
# # Adds:
# # - Fallback BeautifulSoup-based description if Selenium fails
# # - Cleans multiline fields into comma-separated strings
# # - Replaces N/A or blank with "-"
# # ====================================================

# import requests
# from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.options import Options
# import pandas as pd
# import time
# import re

# # ---------------------------
# # Cleaning helper
# # ---------------------------
# def clean_multiline(text):
#     """Convert multiline text to comma-separated clean string."""
#     if not text or str(text).strip().lower() in ["n/a", "na"]:
#         return "-"
#     # Split by newline or carriage return
#     parts = re.split(r'[\n\r]+', str(text))
#     # Remove bracketed references like [1], [ko], [unreliable source?]
#     parts = [re.sub(r'\[.*?\]', '', p).strip() for p in parts if p.strip()]
#     # Join cleaned parts with commas
#     return " , ".join(parts) if parts else "-"

# # ---------------------------
# # Fallback: Description method
# # ---------------------------
# def get_description_fallback(url):
#     headers = {
#         "User-Agent": (
#             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#             "AppleWebKit/537.36 (KHTML, like Gecko) "
#             "Chrome/118.0.0.0 Safari/537.36"
#         )
#     }

#     try:
#         response = requests.get(url, headers=headers, timeout=10)
#         response.raise_for_status()
#         soup = BeautifulSoup(response.text, "html.parser")

#         # Search for section headings
#         for heading_text in ["Synopsis", "Plot", "Premise", "Story", "Summary"]:
#             heading = soup.find(["h2", "h3"], id=heading_text)
#             if heading:
#                 p = heading.find_next("p")
#                 if p and p.get_text(strip=True):
#                     return p.get_text(strip=True)

#         # Fallback to first paragraph
#         first_p = soup.find("p")
#         if first_p:
#             return first_p.get_text(strip=True)
#     except Exception as e:
#         print(f"Fallback failed for {url}: {e}")
#     return "No Description"

# # ---------------------------
# # Setup Selenium WebDriver
# # ---------------------------
# chrome_options = Options()
# chrome_options.add_argument("--headless")
# chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--disable-dev-shm-usage")

# driver = webdriver.Chrome(options=chrome_options)

# # ---------------------------
# # Wikipedia main list
# # ---------------------------
# base_url = "https://en.wikipedia.org/wiki/List_of_South_Korean_dramas"
# driver.get(base_url)
# time.sleep(3)

# # ---------------------------
# # Collect all drama links
# # ---------------------------
# print("Collecting drama links...")
# drama_links = []
# elems = driver.find_elements(By.CLASS_NAME, "div-col")

# for elem in elems:
#     links = elem.find_elements(By.CSS_SELECTOR, "a[href]")
#     for link in links:
#         href = link.get_attribute("href")
#         if href and "wiki" in href and "redlink" not in href:
#             drama_links.append(href)

# drama_links = list(set(drama_links))
# print(f"Found {len(drama_links)} drama links")

# # ---------------------------
# # Scrape each drama page
# # ---------------------------
# titles, alt_titles, writers, directors, casts, genres, networks, episodes, releases, posters, descriptions = [], [], [], [], [], [], [], [], [], [], []

# for i, url in enumerate(drama_links[:10]):  # you can limit with [:10] for testing
#     print(f"\nScraping ({i+1}/{len(drama_links)}): {url}")
#     driver.get(url)
#     time.sleep(1.5)

#     # ---------- Title ----------
#     try:
#         title = driver.find_element(By.ID, "firstHeading").text.strip()
#     except:
#         title = "No Title"

#     # ---------- Defaults ----------
#     alt_title = writer = director = cast = genre = network = episode = release = poster = "N/A"
#     desc = "No Description"

#     # ---------- Infobox ----------
#     try:
#         infobox = driver.find_element(By.CLASS_NAME, "infobox")
#         rows = infobox.find_elements(By.TAG_NAME, "tr")

#         for row in rows:
#             try:
#                 header = row.find_element(By.TAG_NAME, "th").text.lower()
#                 data = row.find_element(By.TAG_NAME, "td")
#             except:
#                 continue

#             if "also known as" in header:
#                 alt_title = data.text
#             elif "written by" in header:
#                 writer = data.text
#             elif "directed by" in header:
#                 director = data.text
#             elif "starring" in header:
#                 cast = data.text
#             elif "genre" in header:
#                 genre = data.text
#             elif "network" in header:
#                 network = data.text
#             elif "episode" in header:
#                 episode = data.text
#             elif "release" in header:
#                 release = data.text

#             # Poster image
#             try:
#                 if "image" in data.get_attribute("class"):
#                     img = data.find_element(By.TAG_NAME, "img")
#                     poster = img.get_attribute("src")
#                     if poster.startswith("//"):
#                         poster = "https:" + poster
#             except:
#                 continue
#     except:
#         pass

#     # ---------- Description ----------
#     try:
#         heading_candidates = ["Synopsis", "Plot", "Premise", "Story"]
#         found_section = None

#         for heading_text in heading_candidates:
#             try:
#                 heading = driver.find_element(
#                     By.XPATH,
#                     f"//h2[.//span[@id='{heading_text}'] or contains(., '{heading_text}')]"
#                 )
#                 found_section = heading
#                 break
#             except:
#                 continue

#         if found_section:
#             next_p = found_section.find_element(By.XPATH, "following-sibling::p")
#             desc = next_p.text.strip()
#         else:
#             desc = driver.find_element(By.CSS_SELECTOR, "p").text.strip()
#     except:
#         pass

#     # ---------- Fallback check ----------
#     if (not desc) or len(desc) < 50 or desc.lower().startswith("no description"):
#         print("Using fallback description...")
#         desc = get_description_fallback(url)

#     # ---------- Clean & Append ----------
#     titles.append(title.strip() if title else "-")
#     alt_titles.append(clean_multiline(alt_title))
#     writers.append(clean_multiline(writer))
#     directors.append(clean_multiline(director))
#     casts.append(clean_multiline(cast))
#     genres.append(clean_multiline(genre))
#     networks.append(network.strip() if network else "-")
#     episodes.append(episode.strip() if episode else "-")
#     releases.append(release.strip() if release else "-")
#     posters.append(poster.strip() if poster else "-")
#     descriptions.append(desc.strip() if desc else "-")

# # ---------------------------
# # Save as CSV
# # ---------------------------
# df = pd.DataFrame({
#     "Title": titles,
#     "Also Known As": alt_titles,
#     "Written By": writers,
#     "Director": directors,
#     "Cast": casts,
#     "Genre": genres,
#     "Network": networks,
#     "Episodes": episodes,
#     "Release Dates": releases,
#     "Poster": posters,
#     "Description": descriptions
# })

# # Replace any remaining invalid/empty values
# df.replace(["N/A", "NA", "", None], "-", inplace=True)

# df.to_csv("kdrama_dataset_detailed_v5.csv", index=False, encoding="utf-8-sig")
# print("\n Done! Data saved to kdrama_dataset_detailed_v5.csv")

# driver.quit()


# ====================================================
# 📺 K-Drama Wikipedia Scraper (Enhanced v7 — Final Clean)
# ====================================================
# Extracts:
# - Title, Also known as, Written by, Directed by, Cast, Genre,
#   Network, Episodes, Release date, Poster image, Description
# Cleans:
# - Removes [1], [citation needed], [ko], etc.
# - Converts multiline entries to proper comma-separated text
# - Extracts release years directly from release date text
# ====================================================

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import re

# ---------------------------
# Cleaning Helpers
# ---------------------------
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
    # Match 4-digit years (e.g., 2004, 2015, 2020)
    years = re.findall(r'(19|20)\d{2}', text)
    # Join unique years (sorted in order of appearance)
    if not years:
        return "-"
    # Reconstruct full years from regex matches (since we only captured first two digits)
    full_years = re.findall(r'(?:19|20)\d{2}', text)
    unique_years = list(dict.fromkeys(full_years))  # preserve order, remove duplicates
    return ", ".join(unique_years)

# ---------------------------
# Fallback: Description method
# ---------------------------
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

# ---------------------------
# Setup Selenium WebDriver
# ---------------------------
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=chrome_options)

# ---------------------------
# Wikipedia main list
# ---------------------------
base_url = "https://en.wikipedia.org/wiki/List_of_South_Korean_dramas"
driver.get(base_url)
time.sleep(3)

# ---------------------------
# Collect all drama links
# ---------------------------
print("Collecting drama links...")
drama_links = []
elems = driver.find_elements(By.CLASS_NAME, "div-col")

for elem in elems:
    links = elem.find_elements(By.CSS_SELECTOR, "a[href]")
    for link in links:
        href = link.get_attribute("href")
        if href and "wiki" in href and "redlink" not in href:
            drama_links.append(href)

drama_links = list(set(drama_links))
print(f"Found {len(drama_links)} drama links")

# ---------------------------
# Scrape each drama page
# ---------------------------
titles, alt_titles, writers, directors, casts, genres, networks, episodes, releases, release_years, posters, descriptions = [], [], [], [], [], [], [], [], [], [], [], []

for i, url in enumerate(drama_links):  # you can limit with [:10] for testing
    print(f"\nScraping ({i+1}/{len(drama_links)}): {url}")
    driver.get(url)
    time.sleep(1.5)

    # ---------- Title ----------
    try:
        title = driver.find_element(By.ID, "firstHeading").text.strip()
    except:
        title = "-"

    # ---------- Defaults ----------
    alt_title = writer = director = cast = genre = network = episode = release = poster = "-"
    desc = "-"

    # ---------- Infobox ----------
    try:
        infobox = driver.find_element(By.CLASS_NAME, "infobox")
        rows = infobox.find_elements(By.TAG_NAME, "tr")

        for row in rows:
            try:
                header = row.find_element(By.TAG_NAME, "th").text.lower()
                data = row.find_element(By.TAG_NAME, "td")
            except:
                continue

            if "also known as" in header:
                alt_title = data.text
            elif "written by" in header:
                writer = data.text
            elif "directed by" in header:
                director = data.text
            elif "starring" in header:
                cast = data.text
            elif "genre" in header:
                genre = data.text
            elif "network" in header:
                network = data.text
            elif "episode" in header:
                episode = data.text
            elif "release" in header:
                release = data.text

            # Poster
            try:
                if "image" in data.get_attribute("class"):
                    img = data.find_element(By.TAG_NAME, "img")
                    poster = img.get_attribute("src")
                    if poster.startswith("//"):
                        poster = "https:" + poster
            except:
                continue
    except:
        pass

    # ---------- Description ----------
    try:
        heading_candidates = ["Synopsis", "Plot", "Premise", "Story"]
        found_section = None

        for heading_text in heading_candidates:
            try:
                heading = driver.find_element(
                    By.XPATH,
                    f"//h2[.//span[@id='{heading_text}'] or contains(., '{heading_text}')]"
                )
                found_section = heading
                break
            except:
                continue

        if found_section:
            next_p = found_section.find_element(By.XPATH, "following-sibling::p")
            desc = clean_description(next_p.text.strip())
        else:
            desc = clean_description(driver.find_element(By.CSS_SELECTOR, "p").text.strip())
    except:
        pass

    # ---------- Fallback ----------
    if (not desc) or len(desc) < 50 or desc.lower().startswith("no description"):
        print("Using fallback description...")
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
df.to_csv("data_scrapper\kdrama_dataset_detailed_v8.csv", index=False, encoding="utf-8-sig")

print("\n Done! Data saved to data_scrapper\kdrama_dataset_detailed_v8.csv")

driver.quit()
