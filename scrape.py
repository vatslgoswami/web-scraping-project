from bs4 import BeautifulSoup
import requests
import re

def scrape_helper(link):
    html_text = requests.get(link).text
    soup = BeautifulSoup(html_text, 'lxml')
    #a) extract all information about the event
    all_info = soup.find('div', class_ = "conflict_content")

    #b)(i) Summary of Event in 20 words
    header = all_info.find('div', class_ = "conflict-header-content")
    summary = header.find('div', class_ = "conflict_title")
    print(f"b) i) Summary (in 20 words): {summary.text}")

    #ii) Start date of Conflict
    bookmark = all_info.find('div', class_ = "conflict_bookmarks")
    stats = bookmark.find_all('div', class_ = "conflict_stats-text-wrap")
    conflict_date = stats[2].find('div', "conflict_stats").text
    print(f"ii) Start date of the conflict: {conflict_date}")

    #iii) Land Area Affected
    area_affected = stats[3].find('div', class_ = 'flex-h').text.replace('.', '')
    print(f"iii) Land area affected: {area_affected}")

    #iv)Sector of Conflict
    insights_wrap = all_info.find_all("div", class_ = "conflict_insights-wrap")
    sector_of_conflict = insights_wrap[0].find('div', class_ = "conflict_insights-name").text
    print(f"iv) Sector of Conflict: {sector_of_conflict}")

    #v) Reasons/Cause of Conflict
    reasons_of_conflict = insights_wrap[1].find('div', class_ = "conflict_insights-name").text
    print(f"v) Reasons/Cause of Conflict: {reasons_of_conflict}")

    #vi) Legal Laws violated
    legal_data = all_info.find('div', id = "legal-data")
    legal_content = legal_data.find_all('div', class_ = "conflict_body-content")
    category_of_law = legal_content[0].find('p', class_ = "conflict_body-block-text").text
    print(f"vi) Legal Laws Violated:")
    print(f"Category of Laws - {category_of_law}")

    laws_violated = legal_content[1].find_all('div', class_ = "conflict_body-block-text is-meium is-leftt-aligned")
    print(f"Precise Laws Violated -")
    if laws_violated:
        for index, law in enumerate(laws_violated):
            if law.get_text(strip=True):
                print(f"{index + 1}. {law.text}")
    else:
        print("Info not available")

    #vii) Demands of the affected Community
    fact_sheet = all_info.find('div', id = "fact-sheet")
    fact_sheet_sections = fact_sheet.find_all('div', class_ = "conflict_block-section")
    demands = fact_sheet_sections[0].find_all('div', class_ = "w-dyn-item")
    print(f"vii) Demands of the affected community:")
    for index, demand in enumerate(demands):
        print(f"{index+1}. {demand.text}")

    #viii) Type of Land
    type_of_land = fact_sheet_sections[1].find_all('div', class_ = "conflict_body-content")[1].find('div', class_ = "flex-h--wrap")
    print(f"viii) Type of land: {type_of_land.text}")

    #ix) Total Investment (if any)
    investment_block = fact_sheet_sections[3].find('div', class_ = "conflict_body-content is-centered")
    if not investment_block:
        print (f"ix) Total Investment (if any): Info not available")
    else:
        first_title = investment_block.find('p', class_ = "conflict_body-block-title").text.strip()
        if first_title == "Total investment involved (in Crores):":
            investment_amount = investment_block.find_all('p', class_="paragraph inline")
            print (f"ix) Total Investment (if any): Rs.{investment_amount[1].text} crores")

    #c) Extract Information from all the secondary urls
    secondary_links = all_info.find("div", class_ = "conflicts_summary").find_all('a')
    print (f"c) Secondary links are:")
    for index, link in enumerate(secondary_links):
        print(f"link {index+1}: {link['href']}")
    print(f"Extracting information from each link and adding to new directory...")
    print(f"Completed")

    
links = ["https://www.landconflictwatch.org/conflicts/handri-neeva-sujala-water-canal-project#", 
         "https://www.landconflictwatch.org/conflicts/kgp-kundli-ghaziabad-palwal-expressway#", 
         "https://www.landconflictwatch.org/conflicts/residents-oppose-waste-disposal-plant-in-bhandut-gujarat#"
         ]

def scrape_and_sort(links):
    for index, link in enumerate(links):
        print(f"Processing Link {index+1}: {link}\n")
        scrape_helper(link)
        print("------------------------------------------------------")

scrape_and_sort(links)

#c) 
