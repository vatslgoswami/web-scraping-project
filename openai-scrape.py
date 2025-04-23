from bs4 import BeautifulSoup
import requests
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import re 
import os

load_dotenv()

client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

#function to extract the header and body text from each secondary article
def extract_secondary_link(link):
    html_text = requests.get(link).text
    soup = BeautifulSoup(html_text, 'lxml')
    header = soup.find('h1').text
    paras = soup.find_all('p')
    body = ''
    for para in paras:
        body += para.text
        body += '\n'
    return header, body

#helper function to chunk the data into tokens of correct size so we can embed it 
def naive_chunker(text, sentences_per_chunk=3, overlap = 1):
    sentences = re.split(r'(?<=[.?!]) +', text)
    chunks = []
    for i in range(0, len(sentences), sentences_per_chunk-overlap):
        chunk = " ".join(sentences[i:i+sentences_per_chunk])
        if chunk.strip():
            chunks.append(chunk)
    return chunks[:len(chunks)-3]

def embed_texts_openai(texts, model="text-embedding-3-small"):
    response = client.embeddings.create(
        input = texts,
        model = model
    )
    return [record.embedding for record in response.data]

#function to chunk and return vector embeddings for each secondary article text
def get_vector_embeddings(text):
    chunks = naive_chunker(text)
    embeddings = embed_texts_openai(chunks)
    embeddings_map = list(zip(chunks, embeddings))
    return embeddings_map

#function that returns the top k chunks of text similar to a query (i.e. relevant data)
def find_top_chunks(query, embeddings_map, top_k=3):
    query_embedding = np.array(embed_texts_openai(query)).reshape(1, -1)
    chunk_texts, chunk_embeddings = zip(*embeddings_map)
    similarities = cosine_similarity(query_embedding, chunk_embeddings)[0]
    most_similar_indices = np.argsort(similarities)[-top_k:][::-1]
    print(most_similar_indices)
    top_chunks = [chunk_texts[i] for i in most_similar_indices]
    for i, sim in enumerate(similarities):
        print(f"Chunk {i}: similarity={sim:.4f}")
    return top_chunks

def scrape_helper(link):
    html_text = requests.get(link).text
    soup = BeautifulSoup(html_text, 'lxml')
    #a) extract all information about the event
    all_info = soup.find('div', class_ = "conflict_content")

    # #b)(i) Summary of Event in 20 words
    # header = all_info.find('div', class_ = "conflict-header-content")
    # summary = header.find('div', class_ = "conflict_title")
    # print(f"b) i) Summary (in 20 words): {summary.text}")

    #ii) Start date of Conflict
    bookmark = all_info.find('div', class_ = "conflict_bookmarks")
    stats = bookmark.find_all('div', class_ = "conflict_stats-text-wrap")
    conflict_date = stats[2].find('div', "conflict_stats").text
    print(f"ii) Start date of the conflict: {conflict_date}")

    #iii) Land Area Affected
    area_affected = stats[3].find('div', class_ = 'flex-h').text.replace('.', '')
    print(f"iii) Land area affected: {area_affected}")

    # #iv)Sector of Conflict
    # insights_wrap = all_info.find_all("div", class_ = "conflict_insights-wrap")
    # sector_of_conflict = insights_wrap[0].find('div', class_ = "conflict_insights-name").text
    # print(f"iv) Sector of Conflict: {sector_of_conflict}")

    # #v) Reasons/Cause of Conflict
    # reasons_of_conflict = insights_wrap[1].find('div', class_ = "conflict_insights-name").text
    # print(f"v) Reasons/Cause of Conflict: {reasons_of_conflict}")

    #vi) Legal Laws violated
    legal_data = all_info.find('div', id = "legal-data")
    legal_content = legal_data.find_all('div', class_ = "conflict_body-content")
    category_of_law = legal_content[0].find('p', class_ = "conflict_body-block-text").text
    print(f"vi) Legal Laws Violated:")
    print(f"Category of Laws - {category_of_law}")

    laws_violated = legal_content[1].find_all('div', class_ = "conflict_body-block-text is-meium is-leftt-aligned")
    laws_ans = ''
    print(f"Precise Laws Violated -")
    if laws_violated:
        for index, law in enumerate(laws_violated):
            if law.get_text(strip=True):
                laws_ans += law.text
                print(f"{index + 1}. {law.text}")
    else:
        print("Info not available")

    #vii) Demands of the affected Community
    fact_sheet = all_info.find('div', id = "fact-sheet")
    fact_sheet_sections = fact_sheet.find_all('div', class_ = "conflict_block-section")
    demands = fact_sheet_sections[0].find_all('div', class_ = "w-dyn-item")
    demand_ans = ""
    print(f"vii) Demands of the affected community:")
    for index, demand in enumerate(demands):
        demand_ans += f"{demand.text}\n"
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
    print(f"-------------------------------------------")
    #c) Extract Information from all the secondary urls
    secondary_links = all_info.find("div", class_ = "conflicts_summary").find_all('a')[1]
    # for link in secondary_links:
    # print (f"c) Secondary links are:")
    # for index, link in enumerate(secondary_links):
    #     print(f"link {index+1}: {link['href']}")
    # print(f"Extracting information from each link and adding to new directory...")
    # print(f"Completed")
    header, body = extract_secondary_link(secondary_links['href'])
    print(f"Embedding info from secondary link: ${secondary_links['href']}")
    embeddings_map = get_vector_embeddings(body)
    print(laws_ans)
    query = f"what are the demands of the affected community? {demand_ans}"
    top_chunks = find_top_chunks(query, embeddings_map, top_k=3)
    for index, chunk in enumerate(top_chunks):
        print(f"{index+1}: {chunk}\n")

    
links = ["https://www.landconflictwatch.org/conflicts/handri-neeva-sujala-water-canal-project#", 
        #  "https://www.landconflictwatch.org/conflicts/kgp-kundli-ghaziabad-palwal-expressway#", 
        #  "https://www.landconflictwatch.org/conflicts/residents-oppose-waste-disposal-plant-in-bhandut-gujarat#"
         ]

def scrape_and_sort(links):
    for index, link in enumerate(links):
        print(f"Processing Link {index+1}: {link}\n")
        scrape_helper(link)
        print("------------------------------------------------------")

scrape_and_sort(links)

#c) 
