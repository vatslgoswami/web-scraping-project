from bs4 import BeautifulSoup
import requests
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re 

tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

#function to extract the header and body text from each secondary article
def extract_secondary_link(link):
    html_text = requests.get(link).text
    soup = BeautifulSoup(html_text, 'lxml')
    header = soup.find('h1').text
    if (soup.find('div', class_ = '_s30J')):
        paras = [soup.find('div', class_ = '_s30J')]
    else:
        paras = soup.find_all('p')
    body = ''
    for para in paras:
        body += para.text
        body += '\n'
    return header, body

#helper function to chunk the data into tokens of correct size so we can embed it 
def sentence_chunker(text, sentences_per_chunk=1, overlap = 0):
    sentences = re.split(r'(?<=[.?!])\s+', text)
    chunks = []
    for i in range(0, len(sentences), sentences_per_chunk-overlap):
        chunk = " ".join(sentences[i:i+sentences_per_chunk])
        if chunk.strip():
            chunks.append(chunk)
    return chunks[:len(chunks)-3]

#function to chunk and return vector embeddings for each secondary article text
def add_vector_embeddings(text, map, link_index):
    chunks = sentence_chunker(text)
    index_list = [link_index] * len(chunks)
    embeddings = model.encode(chunks, show_progress_bar=False)
    embeddings_map = list(zip(chunks, embeddings, index_list))
    map.extend(embeddings_map)
    return map

#function that takes an article link, extracts its text-body and adds it to our embedding_map
def embed_article_text(link, embeddings_map, index):
    header, body = extract_secondary_link(link)
    print(f"{index+1}. Embedding info from: ${link}")
    add_vector_embeddings(body, embeddings_map, index+1)
    return header.strip()

def find_and_embed_all_secondary_links(soup):
    secondary_link_tags = soup.find("div", class_ = "conflicts_summary").find_all('a')
    secondary_links = [link['href'] for link in secondary_link_tags]
    unique_link_map = dict.fromkeys(secondary_links)
    unique_links = list(unique_link_map.keys())
    embeddings_map = []
    article_summaries = []
    print(f"Removing duplicates and creating vector embeddings for all secondary links...")
    for index, link in enumerate(unique_links):
        link_summary = embed_article_text(link, embeddings_map, index)
        article_summaries.append(link_summary)
    print(f"----------------------------------------")
    return article_summaries,embeddings_map

#function that returns the top k chunks of text similar to a query (i.e. relevant data)
def find_top_chunks(query, embeddings_map, top_k=3):
    query_embedding = model.encode(query)
    chunk_texts, chunk_embeddings, sublink_nums = zip(*embeddings_map)
    similarities = cosine_similarity([query_embedding], chunk_embeddings)[0]
    most_similar_indices = np.argsort(similarities)[-top_k:][::-1]
    top_chunks = []
    for index in most_similar_indices:
        if similarities[index] > 0.375:
            top_chunks.append((chunk_texts[index], sublink_nums[index]))
    if top_chunks:    
        return top_chunks
    else:
        return [("No article contains highly relevant information regarding this heading", -1)]

#function to generate queries for vector search from all the primary link answers
def generate_all_queries(answers_dict):
    queries = []
    for question, answer in answers_dict.items():
        queries.append((question, answer))
    return queries

def find_relevant_segments(embeddings_map, queries):
    for index, query in enumerate(queries):
        print(f"{index+2}) {query[0]}:")
        final_query = f"{query[0]}: {query[1]}"
        top_chunks = find_top_chunks(final_query, embeddings_map, top_k=3)
        for index, chunk in enumerate(top_chunks):
            print(f"-> Found the following relevant info in secondary-link #{chunk[1]}: {chunk[0].strip()}\n")

def scrape_helper(link):
    html_text = requests.get(link).text
    soup = BeautifulSoup(html_text, 'lxml')
    #a) extract all information about the event
    all_info = soup.find('div', class_ = "conflict_content")
    final_answers = {}

    #b)(i) Summary of Event in 20 words
    header = all_info.find('div', class_ = "conflict-header-content")
    summary = header.find('div', class_ = "conflict_title")
    print(f"b) i) Summary (in 20 words): {summary.text}")

    #ii) Start date of Conflict
    bookmark = all_info.find('div', class_ = "conflict_bookmarks")
    stats = bookmark.find_all('div', class_ = "conflict_stats-text-wrap")
    conflict_date = stats[2].find('div', "conflict_stats").text
    print(f"ii) Start date of the conflict: {conflict_date}")
    final_answers["Start date (year or month) of the conflict"] = conflict_date

    #iii) Land Area Affected
    area_affected = stats[3].find('div', class_ = 'flex-h').text.replace('.', '')
    print(f"iii) Land area affected: {area_affected}")
    final_answers["How much area of land affected"] = area_affected.replace("ha", " hectares")

    #iv)Sector of Conflict
    insights_wrap = all_info.find_all("div", class_ = "conflict_insights-wrap")
    sector_of_conflict = insights_wrap[0].find('div', class_ = "conflict_insights-name").text
    print(f"iv) Sector of Conflict: {sector_of_conflict}")
    final_answers["What is the sector causing the land conflict"] = sector_of_conflict

    #v) Reasons/Cause of Conflict
    reasons_of_conflict = insights_wrap[1].find('div', class_ = "conflict_insights-name").text
    print(f"v) Reasons/Cause of Conflict: {reasons_of_conflict}")
    final_answers["Reasons/Causes of the conflict"]= reasons_of_conflict

    #vi) Legal Laws violated
    legal_data = all_info.find('div', id = "legal-data")
    legal_content = legal_data.find_all('div', class_ = "conflict_body-content")
    category_of_law = legal_content[0].find('p', class_ = "conflict_body-block-text").text
    print(f"vi) Legal Laws Violated:")
    print(f"Category of Laws - {category_of_law}")
    laws_ans = ''
    laws_ans += f"{category_of_law} "

    laws_violated = legal_content[1].find_all('div', class_ = "conflict_body-block-text is-meium is-leftt-aligned")
    print(f"Precise Laws Violated -")
    if laws_violated:
        for index, law in enumerate(laws_violated):
            if law.get_text(strip=True):
                laws_ans += f"{law.text} "
                print(f"{index + 1}. {law.text}")
    else:
        print("Info not available")
    final_answers["Legal laws violated"] = laws_ans

    #vii) Demands of the affected Community
    fact_sheet = all_info.find('div', id = "fact-sheet")
    fact_sheet_sections = fact_sheet.find_all('div', class_ = "conflict_block-section")
    demands = fact_sheet_sections[0].find_all('div', class_ = "w-dyn-item")
    demand_ans = ""
    print(f"vii) Demands of the affected community:")
    for index, demand in enumerate(demands):
        demand_ans += f"{demand.text} "
        print(f"{index+1}. {demand.text}")
    final_answers["What are the demands of the affected community"] = demand_ans

    #viii) Type of Land
    type_of_land = fact_sheet_sections[1].find_all('div', class_ = "conflict_body-content")[1].find('div', class_ = "flex-h--wrap")
    print(f"viii) Type of land: {type_of_land.text}")
    final_answers["What type of land is being used"] = type_of_land.text

    #ix) Total Investment (if any)
    investment_block = fact_sheet_sections[3].find('div', class_ = "conflict_body-content is-centered")
    if not investment_block:
        print (f"ix) Total Investment (if any): Info not available")
        final_answers["Total investment made"] = ""
    else:
        first_title = investment_block.find('p', class_ = "conflict_body-block-title").text.strip()
        if first_title == "Total investment involved (in Crores):":
            investment_amount = investment_block.find_all('p', class_="paragraph inline")
            print (f"ix) Total Investment (if any): Rs.{investment_amount[1].text} crores")
            final_answers["Total investment made"] = f"{investment_amount[1].text} crores"
    print(f"-------------------------------------------")

    #d) Extract Information from all the secondary urls
    article_summaries, embeddings_map = find_and_embed_all_secondary_links(soup)
    print(f"d) 1) Summary of Each Secondary Link:")
    for index, summary in enumerate(article_summaries):
        print(f"Link #{index+1}: {summary}")
    print("")
    queries = generate_all_queries(final_answers)
    find_relevant_segments(embeddings_map, queries)
    
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
