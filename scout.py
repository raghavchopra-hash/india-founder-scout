#!/usr/bin/env python3
"""
GitHub Founder Scout - India Focus
Finds indie builders in India working on AI/ML and Developer Tools.
Filters out corporate employees - only independent builders.
"""

import requests
import json
import time
import os
from datetime import datetime, timedelta

class IndiaScout:
      def __init__(self, token: str):
                self.token = token
                self.headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                self.base_url = 'https://api.github.com'

          # Keywords that indicate corporate employment (filter OUT)
                self.corporate_keywords = [
                    '@google', '@microsoft', '@meta', '@amazon', '@apple',
                    '@netflix', '@uber', '@airbnb', '@stripe', '@shopify',
                    '@twitter', '@x', '@oracle', '@ibm', '@salesforce',
                    '@adobe', '@vmware', '@cisco', '@intel', '@nvidia',
                    '@redhat', '@databricks', '@snowflake', '@mongodb',
                    '@atlassian', '@github', '@gitlab', '@vercel', '@netlify'
                ]

          # India location keywords
                self.india_keywords = [
                    'india', 'bangalore', 'bengaluru', 'delhi', 'mumbai',
                    'hyderabad', 'chennai', 'pune', 'kolkata', 'gurgaon',
                    'gurugram', 'noida', 'ahmedabad', 'jaipur', 'kochi',
                    'thiruvananthapuram', 'indore', 'bhopal', 'lucknow',
                    'chandigarh', 'coimbatore', 'nagpur', 'vadodara',
                    'indian', 'bharat'
                ]

          # Pioneer/emerging tech keywords (boost score)
                self.pioneer_keywords = [
                    'llm', 'gpt', 'transformer', 'diffusion', 'langchain',
                    'vector', 'embedding', 'rag', 'agent', 'ai', 'ml',
                    'rust', 'zig', 'wasm', 'blockchain', 'web3', 'crypto',
                    'mcp', 'claude', 'openai', 'anthropic'
                ]

      def _request(self, endpoint: str, params: dict = None) -> dict:
                """Make a rate-limited request to GitHub API"""
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, headers=self.headers, params=params)

          if response.status_code == 200:
                        return response.json()
elif response.status_code == 403:
            print(f"Rate limited. Waiting...")
            time.sleep(60)
            return self._request(endpoint, params)
else:
            print(f"Error {response.status_code}: {response.text[:200]}")
              return None

    def is_india_based(self, location: str) -> bool:
              """Check if location indicates India"""
              if not location:
                            return False
                        location_lower = location.lower()
        return any(kw in location_lower for kw in self.india_keywords)

    def is_corporate(self, company: str, bio: str) -> bool:
              """Check if user works at a big company"""
        text = f"{company or ''} {bio or ''}".lower()
        return any(kw in text for kw in self.corporate_keywords)

    def is_indie_builder(self, user_data: dict) -> bool:
              """Check if user is an independent builder"""
        company = user_data.get('company', '') or ''
        bio = user_data.get('bio', '') or ''

        # Filter out corporate employees
        if self.is_corporate(company, bio):
                      return False

        # Positive signals for indie builders
        indie_signals = [
                      'indie', 'founder', 'solo', 'building', 'creator',
                      'maker', 'hacker', 'entrepreneur', 'bootstrapped',
                      'open source', 'oss', 'side project', 'my own'
        ]

        text = f"{company} {bio}".lower()

        # If no company or has indie signals, likely indie
        if not company or company.strip() == '':
                      return True
                  if any(signal in text for signal in indie_signals):
                                return True

        # Small/unknown company is okay
        if not company.startswith('@'):
                      return True

        return False

    def calculate_scores(self, user: dict, repos: list) -> dict:
              """Calculate outlier scores for a developer"""

        total_stars = sum(r.get('stargazers_count', 0) for r in repos)
        total_forks = sum(r.get('forks_count', 0) for r in repos)

        # Growth score - stars relative to account age
        try:
                      created = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
                      account_age_days = max(1, (datetime.now(created.tzinfo) - created).days)
                      growth_score = min(100, (total_stars / account_age_days) * 50)
                  except:
            growth_score = 50

        # Velocity score - recent activity
        recent_repos = [r for r in repos if r.get('pushed_at', '') > (datetime.now() - timedelta(days=90)).isoformat()]
        velocity_score = min(100, len(recent_repos) * 20)

        # Undervalued score - high output, low followers
        followers = user.get('followers', 1) or 1
        output_ratio = (total_stars + len(repos) * 5) / followers
        undervalued_score = min(100, output_ratio * 15)

        # Pioneer score - working on emerging tech
        pioneer_matches = 0
        for repo in repos[:10]:
                      desc = (repo.get('description', '') or '').lower()
                      name = repo.get('name', '').lower()
                      topics = [t.lower() for t in repo.get('topics', [])]

            for keyword in self.pioneer_keywords:
                              if keyword in desc or keyword in name or keyword in topics:
                                                    pioneer_matches += 1
                                                    break

                      pioneer_score = min(100, (pioneer_matches / max(1, min(10, len(repos)))) * 100)

        # Overall score
        overall_score = (
                      growth_score * 0.20 +
                      velocity_score * 0.30 +
                      undervalued_score * 0.25 +
                      pioneer_score * 0.25
        )

        return {
                      'total_stars': total_stars,
                      'total_forks': total_forks,
                      'growth_score': round(growth_score, 1),
                      'velocity_score': round(velocity_score, 1),
                      'undervalued_score': round(undervalued_score, 1),
                      'pioneer_score': round(pioneer_score, 1),
                      'overall_score': round(overall_score, 1)
        }

    def get_top_repos(self, repos: list) -> list:
              """Get top repos with relevant info"""
              sorted_repos = sorted(repos, key=lambda r: r.get('stargazers_count', 0), reverse=True)

        top_repos = []
        for repo in sorted_repos[:5]:
                      if repo.get('fork', False):
                                        continue
                                    top_repos.append({
                                                      'name': repo['name'],
                                                      'description': (repo.get('description') or '')[:200],
                                                      'stars': repo.get('stargazers_count', 0),
                                                      'forks': repo.get('forks_count', 0),
                                                      'language': repo.get('language'),
                                                      'url': repo.get('html_url'),
                                                      'topics': repo.get('topics', [])[:5]
                                    })

        return top_repos[:3]

    def get_languages(self, repos: list) -> list:
              """Get language distribution"""
        languages = {}
        for repo in repos:
                      lang = repo.get('language')
            if lang:
                              languages[lang] = languages.get(lang, 0) + 1

        return sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]

    def search_india_builders(self, max_users: int = 100) -> list:
              """Search for indie builders in India"""

        developers = {}

        # Search queries focused on India + tech
        searches = [
                      'location:india followers:>100 repos:>5',
                      'location:bangalore followers:>50 repos:>3',
                      'location:mumbai followers:>50 repos:>3',
                      'location:delhi followers:>50 repos:>3',
                      'location:hyderabad followers:>50 repos:>3',
                      'location:pune followers:>50 repos:>3',
                      'location:chennai followers:>50 repos:>3',
                      'location:india language:python',
                      'location:india language:typescript',
                      'location:india language:rust',
                      'location:india llm',
                      'location:india ai agent',
        ]

        print("Searching for indie builders in India...")

        for query in searches:
                      print(f"  Searching: {query[:50]}...")

            result = self._request('/search/users', {
                              'q': query,
                              'sort': 'followers',
                              'order': 'desc',
                              'per_page': 30
            })

            if result and 'items' in result:
                              for user in result['items']:
                                                    if user['login'] not in developers:
                                                                              developers[user['login']] = user

                                            time.sleep(2)  # Rate limiting

        print(f"Found {len(developers)} potential developers. Filtering...")

        # Enrich and filter
        enriched = []

        for i, (username, _) in enumerate(list(developers.items())[:max_users * 2]):
                      if len(enriched) >= max_users:
                                        break

            print(f"  [{i+1}] Checking {username}...")

            # Get full user details
            user_data = self._re#!/usr/bin/env python3
"""
GitHub Founder Scout - India Focus
Finds indie builders in India working on AI/ML and Developer Tools.
Filters out corporate employees - only independent builders.
"""

import requests
import json
import time
import os
from datetime import datetime, timedelta

class IndiaScout:
      def __init__(self, token: str):
                self.token = token
        self.headers = {
                      'Authorization': f'token {token}',
                      'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'

        # Keywords that indicate corporate employment (filter OUT)
        self.corporate_keywords = [
                      '@google', '@microsoft', '@meta', '@amazon', '@apple',
                      '@netflix', '@uber', '@airbnb', '@stripe', '@shopify',
                      '@twitter', '@x', '@oracle', '@ibm', '@salesforce',
                      '@adobe', '@vmware', '@cisco', '@intel', '@nvidia',
                      '@redhat', '@databricks', '@snowflake', '@mongodb',
                      '@atlassian', '@github', '@gitlab', '@vercel', '@netlify'
        ]

        # India location keywords
        self.india_keywords = [
                      'india', 'bangalore', 'bengaluru', 'delhi', 'mumbai',
                      'hyderabad', 'chennai', 'pune', 'kolkata', 'gurgaon',
                      'gurugram', 'noida', 'ahmedabad', 'jaipur', 'kochi',
                      'thiruvananthapuram', 'indore', 'bhopal', 'lucknow',
                      'chandigarh', 'coimbatore', 'nagpur', 'vadodara',
                      'indian', 'bharat'
        ]

        # Pioneer/emerging tech keywords (boost score)
        self.pioneer_keywords = [
                      'llm', 'gpt', 'transformer', 'diffusion', 'langchain',
                      'vector', 'embedding', 'rag', 'agent', 'ai', 'ml',
                      'rust', 'zig', 'wasm', 'blockchain', 'web3', 'crypto',
                      'mcp', 'claude', 'openai', 'anthropic'
        ]

    def _request(self, endpoint: str, params: dict = None) -> dict:
              """Make a rate-limited request to GitHub API"""
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
                      return response.json()
elif response.status_code == 403:
            print(f"Rate limited. Waiting...")
            time.sleep(60)
            return self._request(endpoint, params)
else:
            print(f"Error {response.status_code}: {response.text[:200]}")
            return None

    def is_india_based(self, location: str) -
