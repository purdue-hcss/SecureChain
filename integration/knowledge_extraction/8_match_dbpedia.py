import json
from collections import defaultdict
from multiprocessing import Pool

import pandas as pd
import requests
from tqdm import tqdm


def get_top_organisation(query):
    url = f"https://lookup.dbpedia.org/api/search?format=JSON&query={query}"

    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        # 筛选出 type 包含 'Organisation' 的资源
        organisation_results = [
            result for result in data['docs']
        ]

        # 按照 score 降序排序，获取最高的
        if organisation_results:
            top_result = max(organisation_results, key=lambda x: float(x["score"][0]))
            return top_result.get("resource")[0], top_result.get("score")[0]

        else:
            return None

    except requests.exceptions.RequestException:
        return None


def is_valid_organisation(uri):
    sparql_endpoint = "http://dbpedia.org/sparql"
    query = f"""
    ASK {{
      {{
        <{uri}> a <http://dbpedia.org/ontology/Organisation> .
      }} UNION {{
        <{uri}> <http://dbpedia.org/ontology/product> ?product .
      }} UNION {{
        <{uri}> <http://dbpedia.org/property/product> ?product .
      }}
    }}
    """
    params = {
        "query": query,
        "format": "json"
    }

    try:
        response = requests.get(sparql_endpoint, params=params)
        response.raise_for_status()

        data = response.json()
        return data.get("boolean", False)  # Returns True if the ASK query result is true

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while checking organisation validity: {e}")
        return False


def get_location_properties(uri):
    sparql_endpoint = "http://dbpedia.org/sparql"
    query = f"""
    SELECT ?property ?value WHERE {{
      <{uri}> ?property ?value .
      FILTER(CONTAINS(LCASE(STR(?property)), "location"))
    }}
    """
    params = {
        "query": query,
        "format": "json"
    }

    try:
        response = requests.get(sparql_endpoint, params=params)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", {}).get("bindings", [])

        # Group values by property key
        location_properties = defaultdict(set)
        for result in results:
            property_key = result["property"]["value"].split("/")[-1]
            property_value = result["value"]["value"]
            location_properties[property_key].add(property_value)

        # Convert sets to lists for final output
        unique_location_properties = defaultdict(list, {
            key: list(values) for key, values in location_properties.items()
        })

        return unique_location_properties if location_properties else None

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching location properties: {e}")
        return None


def get_resource_info(uri):
    sparql_endpoint = "http://dbpedia.org/sparql"
    query = f"""
    SELECT 
      (COALESCE(?dbp_name, ?foaf_name) AS ?name)
      (COALESCE(?dbp_website, ?foaf_homepage) AS ?website)
      ?product ?headquarter 
    WHERE {{
      OPTIONAL {{ <{uri}> <http://dbpedia.org/property/name> ?dbp_name . }}
      OPTIONAL {{ <{uri}> <http://dbpedia.org/property/website> ?dbp_website . }}
      OPTIONAL {{ <{uri}> <http://dbpedia.org/ontology/product> ?product . }}
      OPTIONAL {{ <{uri}> <http://dbpedia.org/ontology/headquarter> ?headquarter . }}
      OPTIONAL {{ <{uri}> <http://xmlns.com/foaf/0.1/name> ?foaf_name . }}
      OPTIONAL {{ <{uri}> <http://xmlns.com/foaf/0.1/homepage> ?foaf_homepage . }}
    }}
    """
    params = {
        "query": query,
        "format": "json"
    }

    try:
        response = requests.get(sparql_endpoint, params=params)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", {}).get("bindings", [])

        resource_properties = defaultdict(set)
        for result in results:
            for key, value in result.items():
                resource_properties[key].add(value["value"])

        unique_resource_properties = defaultdict(list, {
            key: list(values) for key, values in resource_properties.items()
        })

        return unique_resource_properties if resource_properties else None

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching resource info: {e}")
        return None


def get_vendor_data():
    with open('resources/cpe/vendors.csv', 'r') as f:
        df = pd.read_csv(f)
    return df


def save_info_per_vendor(row: pd.Series):
    vendor = row['vendor']
    top_organisation_uri, relevance_score = get_top_organisation(vendor)
    if top_organisation_uri:
        # print(f"Top organisation for {vendor}: {top_organisation_uri}, relevance score: {relevance_score}")
        if not is_valid_organisation(top_organisation_uri):
            print(f"Top organisation {top_organisation_uri} is not a valid organisation")
            return
        info = get_resource_info(top_organisation_uri)
        locations = get_location_properties(top_organisation_uri)
        if locations:
            info.update(locations)
        info['dbpedia_resource'] = top_organisation_uri
        info['relevance_score'] = relevance_score
        info['vendor'] = vendor
        info['product_count'] = row['count']
        with open('resources/cpe/vendors_wiki_info.jsonl', 'a') as json_file:
            json_file.write(json.dumps(info) + '\n')
    else:
        print(f"No organisation found for {vendor}")
        with open('resources/cpe/vendors_wiki_info.jsonl', 'a') as json_file:
            json_file.write(json.dumps({"vendor": vendor, "product_count": row['count']}) + '\n')


def save_vendors_info():
    vendor_data = get_vendor_data()
    vendor_data = vendor_data.head(1000)

    p = Pool(20)
    for index, row in tqdm(vendor_data.iterrows(), total=vendor_data.shape[0]):
        p.apply_async(save_info_per_vendor, args=(row,))
    p.close()
    p.join()


def group_vendors_info_to_csv():
    with open('resources/cpe/vendors_wiki_info.jsonl', 'r') as f:
        vendors_info = [json.loads(line) for line in f]
    df = pd.DataFrame(vendors_info)
    df = df[['vendor', 'product_count', 'dbpedia_resource', 'relevance_score'] + [col for col in df.columns if
                                                                                  col not in ['vendor', 'product_count',
                                                                                              'dbpedia_resource',
                                                                                              'relevance_score']]]
    df = df.sort_values('product_count', ascending=False)
    df.to_csv('resources/cpe/vendors_wiki_info.csv', index=False)


def main():
    save_vendors_info()
    group_vendors_info_to_csv()


if __name__ == '__main__':
    main()
