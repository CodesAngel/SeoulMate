"""Step 0b: extract each drama's title URL from the listing pages.

Parses every HTML file in html_pages/ (downloaded by Step 0a) and pulls out one
row per drama box: Ranking, Title, Media_Info, Rating, Description, Title_URL,
Image_URL. Title_URL is what Step 1 (step1_download_html.py) needs to fetch
each drama's own page.
"""

import csv
import os

from bs4 import BeautifulSoup

BASE_URL = "https://mydramalist.com"


def extract_drama_data_from_html(html_content):
    """Extracts drama information from one listing page's HTML content."""
    soup = BeautifulSoup(html_content, "html.parser")
    drama_items = soup.find_all("div", class_="box")

    extracted_data = []

    for item in drama_items:
        try:
            title_link_tag = (
                item.find("h6", class_="title").find("a")
                if item.find("h6", class_="title")
                else None
            )
            title = title_link_tag.text.strip() if title_link_tag else "N/A"

            relative_href = (
                title_link_tag.get("href")
                if title_link_tag and title_link_tag.get("href")
                else ""
            )
            title_url = BASE_URL + relative_href if relative_href else "N/A"

            image_tag = (
                item.find("a", class_="block").find("img")
                if item.find("a", class_="block")
                else None
            )
            image_url = (
                (image_tag.get("data-src") or image_tag.get("src")) if image_tag else "N/A"
            )

            ranking_tag = item.find("div", class_="ranking")
            ranking = (
                ranking_tag.find("span").text.strip()
                if ranking_tag and ranking_tag.find("span")
                else "N/A"
            )

            media_info_tag = item.find("span", class_="text-muted")
            media_info = media_info_tag.text.strip() if media_info_tag else "N/A"

            rating_tag = item.find("span", class_="score")
            rating = rating_tag.text.strip() if rating_tag else "N/A"

            content_column = item.find("div", class_="content")
            description_paragraphs = (
                content_column.find_all("p") if content_column else []
            )
            description = (
                description_paragraphs[-1].text.strip() if description_paragraphs else "N/A"
            )
            if description.endswith("…"):
                description = description[:-1].strip()

            extracted_data.append(
                {
                    "Ranking": ranking,
                    "Title": title,
                    "Media_Info": media_info,
                    "Rating": rating,
                    "Description": description,
                    "Title_URL": title_url,
                    "Image_URL": image_url,
                }
            )
        except Exception as e:
            print(f"Error processing one drama entry: {e}")
            continue

    return extracted_data


def extract_from_folder(folder_path, output_csv):
    """Loops through all .html files in folder_path and writes one combined CSV."""
    all_data = []

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".html"):
            file_path = os.path.join(folder_path, filename)
            print(f"Processing file: {filename}")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                data = extract_drama_data_from_html(html_content)
                all_data.extend(data)
            except Exception as e:
                print(f"Failed to process {filename}: {e}")

    if all_data:
        keys = all_data[0].keys()
        with open(output_csv, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_data)
        print(f"\nSuccessfully saved {len(all_data)} entries to '{output_csv}'")
    else:
        print("\nNo data extracted from any HTML files.")


if __name__ == "__main__":
    folder_path = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\html_pages"
    output_csv = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\mydramalist_data.csv"
    extract_from_folder(folder_path, output_csv)
