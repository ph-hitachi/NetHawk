import re
import requests
from bs4 import BeautifulSoup
from googlesearch import search
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)


def cve_details_provider(tect_name, page: int = 1, link_limit: int = 5):
    # Constructing the CVE Details search URL with specific vulnerability filters.
    url = (
        "https://www.cvedetails.com/vulnerability-search.php?"  # Base search URL
        f"f=1"  # Activate the search form (required field)
        f"&vendor={tect_name}"  # Dynamically insert the vendor name (e.g., 'microsoft', 'apache')
        # Apply specific vulnerability filters:
        f"&optmemory_corruption=1"  # Include memory corruption vulnerabilities
        f"&optsql_injection=1"      # Include SQL injection vulnerabilities
        f"&optdir_traversal=1"      # Include directory traversal vulnerabilities
        f"&optfileinc=1"            # Include file inclusion vulnerabilities
        f"&optxxe=1"                # Include XML External Entity (XXE) vulnerabilities
        f"&optssrf=1"               # Include Server-Side Request Forgery (SSRF) vulnerabilities
        f"&optexeccode=1"           # Include remote/unauthorized code execution vulnerabilities
        f"&optgainpriv=1"           # Include privilege escalation vulnerabilities
        f"&page={page}"  # Specify the page number for paginated results
    )


    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch CVE data: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    cve_blocks = soup.find_all("div", class_="border-top py-3 px-2 hover-bg-light", attrs={"data-tsvfield": "cveinfo"})

    cve_ids = []

    for block in cve_blocks:
        exploit_div = block.find("div", attrs={"data-tsvfield": "exploitExistsPotential", "title": "Potential exploit exists"})
        if exploit_div:
            cve_id_tag = block.find("a", href=True)
            if cve_id_tag:
                cve_ids.append(cve_id_tag.text.strip())

    if not cve_ids:
        logging.info("No CVEs with 'Potential exploit exists' found.")
        return

    cve_links = defaultdict(list)

    for cve_id in cve_ids:
        query = f"{cve_id} site:github.com"
        logging.info(f"[+] Searching for: {query}")

        try:
            results = search(query, num_results=link_limit, lang="en")
            
            for link in results:
                cve_id = None
                match = re.search(r"(CVE-\d{4}-\d{4,7})", link, re.IGNORECASE)
                if match:
                    cve_id = match.group(1).upper()
                
                # cve_id = self.extract_cve_from_link(link)
                if not cve_id:
                    continue

                if link not in cve_links[cve_id]:
                    cve_links[cve_id].append(link)

        except Exception as e:
            logging.warning(f"[!] Google search failed for {cve_id}: {e}")

    # Sort by year descending
    sorted_cves = sorted(cve_links.items(), key=lambda x: int(x[0].split("-")[1]), reverse=True)

    for cve_id, links in sorted_cves:
        print(f"\n[*] CVE-ID: {cve_id}")
        print("    Scripts:")
        for link in links:
            print(f"    - {link}")


if __name__ == "__main__":
    cve_details_provider('Grafana', page=1, link_limit=3)
