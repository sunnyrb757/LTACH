#!/usr/bin/env python3
"""
SEO Analyzer Tool
This script crawls a website starting from a given URL and performs a basic on-page SEO audit.

Usage:
    python seo_analyzer.py https://example.com

Requirements:
    pip install -r requirements.txt

"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, urlparse
import argparse
import sys


def analyze_url(url, session):
    """
    Analyzes a single URL for on-page SEO metrics.

    Args:
        url (str): The URL to analyze.
        session (requests.Session): The session object to use for HTTP requests.

    Returns:
        dict: A dictionary containing the SEO analysis results for the URL.
    """
    results = {'URL': url}
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.text, 'lxml')

        # --- On-Page SEO Basics ---
        # 1. Title Tag
        title_tag = soup.find('title')
        results['Title'] = title_tag.text.strip() if title_tag else 'MISSING'
        results['Title Length'] = len(results['Title']) if title_tag else 0

        # 2. Meta Description
        meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
        results['Meta Description'] = meta_desc_tag['content'].strip() if meta_desc_tag and meta_desc_tag.get('content') else 'MISSING'
        results['Meta Description Length'] = len(results['Meta Description']) if meta_desc_tag and meta_desc_tag.get('content') else 0

        # 3. H1 Tags
        h1_tags = soup.find_all('h1')
        results['H1 Count'] = len(h1_tags)
        results['H1 Text'] = [h1.text.strip() for h1 in h1_tags] if h1_tags else 'MISSING'

        # --- Content Analysis ---
        # Word count
        results['Word Count'] = len(soup.get_text().split())

        # --- Image SEO ---
        images = soup.find_all('img')
        results['Image Count'] = len(images)
        missing_alt_text_count = sum(1 for img in images if not img.get('alt', '').strip())
        results['Images Missing Alt Text'] = missing_alt_text_count

        # --- Link Analysis ---
        base_netloc = urlparse(url).netloc
        internal_links = 0
        broken_links_list = []

        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            # Join relative URLs with the base URL to make them absolute
            absolute_url = urljoin(url, href)
            parsed_absolute_url = urlparse(absolute_url)

            # Check if it's an internal link
            if parsed_absolute_url.netloc == base_netloc:
                internal_links += 1
                try:
                    # Use a HEAD request for efficiency to check link status
                    link_response = session.head(absolute_url, timeout=5, allow_redirects=True)
                    if link_response.status_code >= 400:
                        broken_links_list.append(absolute_url)
                except requests.RequestException:
                    # Catches timeouts, connection errors, etc.
                    broken_links_list.append(f"{absolute_url} (Error: Connection Failed)")

        results['Internal Links Count'] = internal_links
        results['Broken Internal Links Count'] = len(broken_links_list)
        results['Broken Internal Links'] = ', '.join(broken_links_list) if broken_links_list else 'None'

    except requests.RequestException as e:
        results['Error'] = f"Request failed: {e}"
    except Exception as e:
        results['Error'] = f"An unexpected error occurred: {e}"

    return results


def discover_internal_links(start_url, session):
    """
    Crawls the starting URL to find all unique internal links.

    Args:
        start_url (str): The URL to start crawling from.
        session (requests.Session): The requests session object.

    Returns:
        set: A set of unique absolute URLs found on the starting page.
    """
    try:
        response = session.get(start_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        internal_links = {start_url} # Use a set to store unique links
        base_netloc = urlparse(start_url).netloc

        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Ignore anchor links and javascript links
            if href.startswith('#') or href.startswith('javascript:'):
                continue

            absolute_url = urljoin(start_url, href)
            parsed_url = urlparse(absolute_url)

            # Add to set if it's on the same domain and not an anchor
            if parsed_url.netloc == base_netloc:
                # Clean off any fragments
                clean_url = parsed_url._replace(fragment="").geturl()
                internal_links.add(clean_url)
        
        return list(internal_links)

    except requests.RequestException as e:
        print(f"Error: Could not crawl {start_url} to discover links. {e}", file=sys.stderr)
        return [start_url] # Return the starting URL at least
    except Exception as e:
        print(f"An unexpected error occurred during link discovery: {e}", file=sys.stderr)
        return [start_url]


def main():
    """
    Main function to run the SEO analyzer.
    """
    parser = argparse.ArgumentParser(
        description="A Python script to perform a basic on-page SEO audit for a given website.",
        epilog="Example: python seo_analyzer.py https://moderncityassociatesllc.com"
    )
    parser.add_argument("url", help="The starting URL of the website to analyze (e.g., https://yourwebsite.com).")
    
    args = parser.parse_args()
    start_url = args.url

    print(f"Starting SEO Analysis for: {start_url}")

    # Use a session object to reuse TCP connections for performance
    with requests.Session() as session:
        # Set a user-agent to mimic a real browser
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        
        print("Discovering internal links from the homepage...")
        urls_to_check = discover_internal_links(start_url, session)
        print(f"Found {len(urls_to_check)} unique pages to analyze.")
        
        all_results = []
        for i, url in enumerate(urls_to_check):
            print(f"Analyzing ({i+1}/{len(urls_to_check)}): {url}")
            analysis = analyze_url(url, session)
            all_results.append(analysis)

    # Convert results to a pandas DataFrame for easy viewing and CSV export
    df = pd.DataFrame(all_results)

    # Reorder columns for a more logical layout
    column_order = [
        'URL', 'Title', 'Title Length', 'Meta Description', 'Meta Description Length',
        'H1 Count', 'H1 Text', 'Word Count', 'Image Count', 'Images Missing Alt Text',
        'Internal Links Count', 'Broken Internal Links Count', 'Broken Internal Links', 'Error'
    ]
    # Filter out columns that might not exist if there are errors across the board
    df = df.reindex(columns=[col for col in column_order if col in df.columns])


    # Save the report to a CSV file
    try:
        output_filename = 'seo_audit_report.csv'
        df.to_csv(output_filename, index=False, encoding='utf-8')
        print(f"\nAnalysis complete! Report saved to '{output_filename}'")
        # Display the DataFrame in the console
        print("\n--- SEO Audit Report ---")
        print(df.to_string())
        print("------------------------")
    except Exception as e:
        print(f"\nError saving CSV file: {e}")


if __name__ == "__main__":
    main()
