from numpy import datetime64
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import os.path
import pandas as pd
import imdb

files_list = r"C:\Users\User\Desktop\CS\sem 6\humanities\links.txt"
english_names = r"C:\Users\User\Desktop\CS\sem 6\humanities\movies_heb_eng.csv"
files_metadata = r"C:\Users\User\Desktop\CS\sem 6\humanities\metadata\metadata.csv"
archive_base_url = "https://www.archives.gov.il"

def get_links (url):
    '''
    gets all cases' links and saves them in the file represented by 'files_list'
    '''
    driver = webdriver.Chrome()

    driver.get(url)
    time.sleep(60)
    soup = BeautifulSoup(driver.page_source,"lxml")

    elements = soup.findAll("product-card")
    links = []
    # elements = [x for x in elements if x.find('a')['href']]
    for element in elements:
        try:
            links.append(archive_base_url + element.find('a')['href'])
        except:
            continue

    driver.close()

    with open('links.txt', 'w') as f:
        for link in links:
            f.write(link + '\n')

def get_metadata (driver, url):
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source,"lxml")
    
    movie_name = soup.find("div", {"id": "item-data"}).find("h1").text
    movie_name = movie_name.split('-')
    if len(movie_name) > 1:
        movie_name = movie_name[1].strip()
    else:
        movie_name = movie_name[0].strip()
    outputValues = {'name' : movie_name}

    metadata = soup.find("div", {"id": "item-data"}).find("ul")
    i = 1
    for element in metadata.li.next_siblings:
        if element.name:
            title = element.find("h2")
            if title:
                title = title.text
            else:
                title = str(title) + str(i)
            content = element.find("span")
            if content:
                content = content.text
            outputValues[title] = content
                
    outputValues['archive link'] = url

    return outputValues

def read_archive(inputfile,outputfile,begin_at_line=0):
    driver = webdriver.Chrome()
    
    # incase we already got some metadata and want to append
    if os.path.isfile(outputfile):
        df = pd.read_csv(outputfile)
        counter = df.shape[0]
    else:
        counter = 0

    try:
        with open(inputfile,'r', encoding="utf8") as links:
            links = links.read().split("\n")[begin_at_line:]
            for url in links[counter:]: # continue from the previous link
                try:
                    relevant_metadata = get_metadata(driver, url)
                    if counter > 0:
                        df = df.append(relevant_metadata, ignore_index=True)
                    else:
                        df = pd.DataFrame(relevant_metadata, index=[counter])
                    print(df)

                except Exception as ex:
                    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                    message = template.format(type(ex).__name__, ex.args)
                    print(message)
                
                counter = counter + 1

    except:
        print("Encountered some error")
        driver.close()

    finally:
        df.to_csv(files_metadata, index=False)

def clean_metadata(df):  
    # remove duplicate english named columns
    df = df.iloc[:, :-7] # drop last 7 columns

    # rename columns to english names
    df.columns = ['Name', 'None1', 'Case type', 'Material period from', 'Material period up to', 'Description', 'File number to quote', 'Creating body position', 'Subjects', 'Bodies', 'Place', 'Events', 'Archive Link', 'Persons']

    df.drop(columns='None1', inplace=True) # useless column

    df = df[~df['Description'].str.contains('מחזה', na=True)]
    return df

def imdb_metadata(df):
    db = imdb.IMDb()
    origin_country = []
    genre = []
    for i, row in df.iterrows():
        print("{}: getting imdb metadata".format(i))
        imdb_id = row['imdb_id'][2:]
        movie = db.get_movie(imdb_id)
        origin_country.append(movie['country'])
        genre.append(movie['genre'])

    df['genre'] = genre
    df['origin country'] = origin_country

def main():
    # assuming for now there are no more than 8K items in the movie category at the archive
    get_links(r"https://www.archives.gov.il/catalogue/group/1?objHier_archiveName_ss=%D7%A6%D7%A0%D7%96%D7%95%D7%A8%D7%94%20%D7%9C%D7%A1%D7%A8%D7%98%D7%99%D7%9D%20%D7%95%D7%9E%D7%97%D7%96%D7%95%D7%AA&kw=%D7%94%D7%9E%D7%95%D7%A2%D7%A6%D7%94%20%D7%9C%D7%91%D7%99%D7%A7%D7%95%D7%A8%D7%AA%20%D7%A1%D7%A8%D7%98%D7%99%D7%9D&scanned_items=true&itemsPerPage=8000")

    # read archive metadata and save to metadata.csv
    read_archive(files_list, files_metadata, 0)

    # clean the metadata file from uneccessary columns etc..
    df = clean_metadata(pd.read_csv(files_metadata))

    # merge data given by Guy Mor about the english names of movies with our data
    df_english = pd.read_csv(english_names)

    df = df.merge(df_english, left_on='Name', right_on='hebrewTitle')
    df['IMDB Link'] = 'https://www.imdb.com/title/' + df['imdb_id']

    # get additional metadata from IMDb
    imdb_metadata(df)

    df.to_csv("temp.csv", encoding='utf-8', index=False)


if __name__ == "__main__":
    # clean the characters '[] from the imdb gathered data because it returns as list 
    # import re
    # chars_to_remove = ["'", '[', ']']
    # regular_expression = '[' + re.escape (''. join (chars_to_remove)) + ']'
    # df = pd.read_csv('temp_utf8.csv')
    # df['origin country'] = df['origin country'].str.replace(regular_expression, '', regex=True)
    # df['genre'] = df['genre'].str.replace(regular_expression, '', regex=True)
    # df.to_csv("temp_proc.csv")

    # clean the non matching rows which the year of material is before the movie even released
    # df = pd.read_csv('final_clean.csv')
    # to_drop = []
    # for i, row in df.iterrows():
    #     material_year = int(row['Material period up to'].split('/')[-1])
    #     # print(material_year, row['year'])
    #     if material_year < row['year']:
    #         to_drop.append(i)            
    # df = df.drop(to_drop)
    # df.to_csv("final_clean_years.csv", index=False)

    main()