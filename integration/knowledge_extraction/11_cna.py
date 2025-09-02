import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from tqdm import tqdm


def parse_cna_table() -> list:
    # open a local html file
    with open('resources/cna/List Of Partners _ CVE.html', 'r') as file:
        content = file.read()

    # Parse the HTML content
    soup = BeautifulSoup(content, 'html.parser')

    # Find the table containing the CNA list
    table = soup.find('table')

    # Extract the table rows
    return table.find_all('tr')


def crawl_partner(row: BeautifulSoup, driver) -> tuple:
    # Extract table headings
    headings = row.find_all('th')
    # Extract basic CNA info
    cna_name = headings[0].text.strip()
    # Try to find homepage link (if available)
    cna_page_tag = headings[0].find('a')
    cna_page = cna_page_tag['href'] if cna_page_tag else ""

    # Extract table columns
    cols = row.find_all('td')
    # Extract basic CNA info
    cna_scope = cols[0].text.strip()

    # Try to find homepage link (if available)
    homepage_tag = cols[0].find('a')
    homepage = homepage_tag['href'] if homepage_tag else ""

    # Placeholder for contact email (not directly on the table)
    email = ""

    # You may need to visit the CNA's specific page if emails are listed there
    if cna_page != "":
        try:
            driver.get(cna_page)
            cna_soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Example: Find an email address in the page (you might need to adjust based on actual structure)
            email_tag = cna_soup.find('a', href=lambda href: href and "mailto:" in href)
            email = email_tag['href'].replace("mailto:", "") if email_tag else ""
        except Exception as e:
            print(f"Error fetching CNA page: {cna_page}")
            print(e)

    return cna_name, cna_scope, homepage, email


def crawl_cna_info():
    # Parse the CNA table
    rows = parse_cna_table()

    # Initialize the Chrome driver
    driver = webdriver.Chrome()

    # Prepare data storage
    cna_data = [crawl_partner(row, driver) for row in tqdm(rows[1:])]

    # Convert to a DataFrame
    df = pd.DataFrame(cna_data, columns=['CNA Name', 'Scope', 'Homepage', 'Email'])

    # Save the DataFrame to a CSV file
    df.to_csv('cna_list.csv', index=False)

    driver.quit()


def main():
    crawl_cna_info()


if __name__ == '__main__':
    main()
