#!/usr/bin/env python3
"""
Founder Scout - Advanced Discovery System
Finds exceptional founders through multiple signals:
1. GitHub Trending repos & their creators
2. Star velocity (repos gaining traction fast)
3. Contributors to hot open source projects
4. Active discussion participants
5. HuggingFace ML builders

Runs automatically via GitHub Actions.
"""

import requests
import json
import time
import os
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from collections import defaultdict


class TrendingScout:
    """Discover founders through GitHub Trending"""

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'

    def get_trending_repos(self, since: str = 'daily', language: str = None) -> list:
        """Scrape GitHub trending page"""
        url = 'https://github.com/trending'
        if language:
            url += f'/{language}'
        url += f'?since={since}'

        try:
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(resp.text, 'html.parser')

            repos = []
            for article in soup.select('article.Box-row'):
                h2 = article.select_one('h2 a')
                if h2:
                    repo_path = h2.get('href', '').strip('/')
                    if repo_path:
                        repos.append(repo_path)

            return repos[:25]
        except Exception as e:
            print(f"Error fetching trending: {e}")
            return []

    def get_repo_owner_details(self, repo_path: str) -> dict:
        """Get details about a repo owner"""
        try:
            owner = repo_path.split('/')[0]
            user_resp = requests.get(f'{self.base_url}/users/{owner}', headers=self.headers)
            if user_resp.status_code != 200:
                return None

            user = user_resp.json()
            location = (user.get('location') or '').lower()
            india_keywords = ['india', 'bangalore', 'bengaluru', 'mumbai', 'delhi',
                           'hyderabad', 'chennai', 'pune', 'kolkata', 'gurgaon',
                           'noida', 'ahmedabad', 'jaipur', 'kochi', 'indore']

            if not any(kw in location for kw in india_keywords):
                return None

            repo_resp = requests.get(f'{self.base_url}/repos/{repo_path}', headers=self.headers)
            repo = repo_resp.json() if repo_resp.status_code == 200 else {}

            return {
                'username': user.get('login'),
                'name': user.get('name') or user.get('login'),
                'bio': user.get('bio') or '',
                'location': user.get('location') or '',
                'followers': user.get('followers', 0),
                'public_repos': user.get('public_repos', 0),
                'trending_repo': repo_path,
                'repo_stars': repo.get('stargazers_count', 0),
                'repo_description': repo.get('description', ''),
                'discovery_method': 'trending',
                'avatar_url': user.get('avatar_url', ''),
                'html_url': user.get('html_url', ''),
                'company': user.get('company') or '',
                'blog': user.get('blog') or '',
                'twitter': user.get('twitter_username') or ''
            }
        except Exception as e:
            print(f"Error getting owner details for {repo_path}: {e}")
            return None

    def discover_from_trending(self) -> list:
        """Find Indian founders from trending repos"""
        print("Scanning GitHub Trending...")
        founders = []
        seen = set()

        languages = [None, 'python', 'typescript', 'javascript', 'rust', 'go']
        periods = ['daily', 'weekly']

        for lang in languages:
            for period in periods:
                repos = self.get_trending_repos(since=period, language=lang)
                for repo in repos:
                    owner = repo.split('/')[0]
                    if owner not in seen:
                        seen.add(owner)
                        details = self.get_repo_owner_details(repo)
                        if details:
                            founders.append(details)
                            print(f"  Found: {details['name']} (trending: {repo})")
                        time.sleep(0.5)

        return founders


class StarVelocityScout:
    """Find repos/founders with high star velocity"""

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'

    def find_rising_stars(self, days: int = 7, min_stars: int = 50) -> list:
        """Find repos created recently with fast star growth"""
        print("Finding repos with high star velocity...")
        founders = []
        seen = set()

        date_threshold = (datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d')

        queries = [
            f'created:>{date_threshold} stars:>{min_stars} language:python',
            f'pushed:>{date_threshold} stars:>100 language:python topic:llm',
            f'pushed:>{date_threshold} stars:>100 language:python topic:ai',
            f'pushed:>{date_threshold} stars:>50 topic:langchain',
            f'pushed:>{date_threshold} stars:>50 topic:agents',
        ]

        for query in queries:
            try:
                resp = requests.get(
                    f'{self.base_url}/search/repositories',
                    headers=self.headers,
                    params={'q': query, 'sort': 'stars', 'per_page': 20}
                )

                if resp.status_code == 200:
                    for repo in resp.json().get('items', []):
                        owner_login = repo['owner']['login']
                        if owner_login not in seen:
                            seen.add(owner_login)

                            user_resp = requests.get(
                                f"{self.base_url}/users/{owner_login}",
                                headers=self.headers
                            )
                            if user_resp.status_code == 200:
                                user = user_resp.json()
                                location = (user.get('location') or '').lower()

                                india_keywords = ['india', 'bangalore', 'bengaluru', 'mumbai',
                                               'delhi', 'hyderabad', 'chennai', 'pune']

                                if any(kw in location for kw in india_keywords):
                                    founders.append({
                                        'username': user.get('login'),
                                        'name': user.get('name') or user.get('login'),
                                        'bio': user.get('bio') or '',
                                        'location': user.get('location') or '',
                                        'followers': user.get('followers', 0),
                                        'public_repos': user.get('public_repos', 0),
                                        'trending_repo': repo['full_name'],
                                        'repo_stars': repo['stargazers_count'],
                                        'repo_description': repo.get('description', ''),
                                        'discovery_method': 'star_velocity',
                                        'avatar_url': user.get('avatar_url', ''),
                                        'html_url': user.get('html_url', ''),
                                        'company': user.get('company') or '',
                                        'blog': user.get('blog') or '',
                                        'twitter': user.get('twitter_username') or ''
                                    })
                                    print(f"  Rising: {user.get('name')} ({repo['stargazers_count']} stars)")

                            time.sleep(0.3)

                time.sleep(1)
            except Exception as e:
                print(f"Error in star velocity search: {e}")

        return founders


class ContributorScout:
    """Find contributors to popular/trending projects"""

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'

    def get_hot_project_contributors(self) -> list:
        """Find Indian contributors to hot AI/ML projects"""
        print("Finding contributors to hot projects...")

        hot_projects = [
            'langchain-ai/langchain',
            'langchain-ai/langgraph',
            'huggingface/transformers',
            'run-llama/llama_index',
            'chroma-core/chroma',
            'microsoft/autogen',
            'crewAIInc/crewAI',
        ]

        founders = []
        seen = set()

        for project in hot_projects:
            try:
                resp = requests.get(
                    f'{self.base_url}/repos/{project}/contributors',
                    headers=self.headers,
                    params={'per_page': 30}
                )

                if resp.status_code == 200:
                    for contrib in resp.json():
                        login = contrib['login']
                        if login not in seen and contrib['contributions'] >= 5:
                            seen.add(login)

                            user_resp = requests.get(
                                f'{self.base_url}/users/{login}',
                                headers=self.headers
                            )

                            if user_resp.status_code == 200:
                                user = user_resp.json()
                                location = (user.get('location') or '').lower()

                                india_keywords = ['india', 'bangalore', 'bengaluru', 'mumbai',
                                               'delhi', 'hyderabad', 'chennai', 'pune']

                                if any(kw in location for kw in india_keywords):
                                    founders.append({
                                        'username': user.get('login'),
                                        'name': user.get('name') or user.get('login'),
                                        'bio': user.get('bio') or '',
                                        'location': user.get('location') or '',
                                        'followers': user.get('followers', 0),
                                        'public_repos': user.get('public_repos', 0),
                                        'contributed_to': project,
                                        'contributions': contrib['contributions'],
                                        'discovery_method': 'contributor',
                                        'avatar_url': user.get('avatar_url', ''),
                                        'html_url': user.get('html_url', ''),
                                        'company': user.get('company') or '',
                                        'blog': user.get('blog') or '',
                                        'twitter': user.get('twitter_username') or ''
                                    })
                                    print(f"  Contributor: {user.get('name')} ({contrib['contributions']} commits to {project})")

                            time.sleep(0.3)

                time.sleep(1)
            except Exception as e:
                print(f"Error checking {project}: {e}")

        return founders


class KeywordScout:
    """Keyword-based search for founders"""

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'

    def search(self) -> list:
        """Execute keyword searches"""
        print("Running keyword searches...")

        searches = [
            '"Founder" "Building" "agentic" location:India',
            '"Co-founder" OR "CTO" "Agentic" location:India',
            '"Building" "langgraph" location:India',
            '"Founder" "langchain" location:India',
            '"Founder" OR "CTO" "LLM" location:India',
            '"Stealth" AND "agentic" location:India',
            'location:india followers:>100 repos:>10',
            'location:bangalore followers:>50 "founder"',
            'location:india "YC" OR "Y Combinator"',
        ]

        founders = []
        seen = set()

        for query in searches:
            try:
                resp = requests.get(
                    f'{self.base_url}/search/users',
                    headers=self.headers,
                    params={'q': query, 'per_page': 15}
                )

                if resp.status_code == 200:
                    for user in resp.json().get('items', []):
                        if user['login'] not in seen:
                            seen.add(user['login'])

                            profile_resp = requests.get(
                                f"{self.base_url}/users/{user['login']}",
                                headers=self.headers
                            )

                            if profile_resp.status_code == 200:
                                profile = profile_resp.json()
                                founders.append({
                                    'username': profile.get('login'),
                                    'name': profile.get('name') or profile.get('login'),
                                    'bio': profile.get('bio') or '',
                                    'location': profile.get('location') or '',
                                    'followers': profile.get('followers', 0),
                                    'public_repos': profile.get('public_repos', 0),
                                    'discovery_method': 'keyword',
                                    'avatar_url': profile.get('avatar_url', ''),
                                    'html_url': profile.get('html_url', ''),
                                    'company': profile.get('company') or '',
                                    'blog': profile.get('blog') or '',
                                    'twitter': profile.get('twitter_username') or ''
                                })

                            time.sleep(0.3)

                time.sleep(1)
            except Exception as e:
                print(f"Search error: {e}")

        return founders


class HuggingFaceScout:
    """Find ML builders on HuggingFace"""

    def __init__(self):
        self.base_url = 'https://huggingface.co/api'

    def search_indian_ml_builders(self, max_users: int = 20) -> list:
        """Find Indian ML builders with models on HuggingFace"""
        print("Searching HuggingFace for ML builders...")
        founders = []
        search_terms = ['india', 'hindi', 'bengali', 'tamil', 'indic']

        for term in search_terms:
            try:
                resp = requests.get(f'{self.base_url}/models', params={'search': term, 'limit': 20})

                if resp.status_code == 200:
                    for model in resp.json():
                        author = model.get('author', '')
                        if author and author not in [f['username'] for f in founders]:
                            founders.append({
                                'username': author,
                                'name': author,
                                'bio': f"ML Builder - {model.get('modelId', '')}",
                                'location': 'India (HuggingFace)',
                                'followers': model.get('downloads', 0),
                                'public_repos': 0,
                                'discovery_method': 'huggingface',
                                'avatar_url': f'https://huggingface.co/avatars/{author}',
                                'html_url': f'https://huggingface.co/{author}',
                                'hf_model': model.get('modelId', ''),
                                'hf_downloads': model.get('downloads', 0)
                            })

                time.sleep(0.5)
            except Exception as e:
                print(f"HuggingFace search error: {e}")

        return founders[:max_users]


def calculate_score(founder: dict) -> dict:
    """Calculate founder scores"""
    followers = founder.get('followers', 0)
    repo_stars = founder.get('repo_stars', 0)
    growth = min(100, (followers / 10) + (repo_stars / 5))

    contributions = founder.get('contributions', 0)
    velocity = min(100, 50 + (contributions * 2))

    repos = founder.get('public_repos', 0)
    hidden = min(100, (repos * 3) - (followers / 20) + 50)

    method_bonus = {
        'trending': 30,
        'star_velocity': 25,
        'contributor': 20,
        'keyword': 10,
        'huggingface': 15
    }
    pioneer = 50 + method_bonus.get(founder.get('discovery_method', ''), 0)

    bio = (founder.get('bio') or '').lower()
    if any(kw in bio for kw in ['founder', 'ceo', 'cto', 'building', 'yc']):
        pioneer += 15
    if any(kw in bio for kw in ['ai', 'ml', 'llm', 'agent', 'langchain']):
        velocity += 10

    overall = (growth * 0.25) + (velocity * 0.25) + (hidden * 0.2) + (pioneer * 0.3)

    founder['scores'] = {
        'growth': round(growth, 1),
        'velocity': round(velocity, 1),
        'hidden_gem': round(hidden, 1),
        'pioneer': round(pioneer, 1),
        'overall_score': round(overall, 1)
    }
    founder['overall_score'] = round(overall, 1)

    return founder


def main():
    """Run all discovery methods"""
    print("=" * 50)
    print("FOUNDER SCOUT - Advanced Discovery System")
    print("=" * 50)

    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("GITHUB_TOKEN not set")
        return

    all_founders = []
    seen_usernames = set()

    # 1. Trending Discovery
    try:
        trending = TrendingScout(token)
        for f in trending.discover_from_trending():
            if f['username'] not in seen_usernames:
                seen_usernames.add(f['username'])
                all_founders.append(f)
    except Exception as e:
        print(f"Trending scout error: {e}")

    # 2. Star Velocity
    try:
        velocity = StarVelocityScout(token)
        for f in velocity.find_rising_stars():
            if f['username'] not in seen_usernames:
                seen_usernames.add(f['username'])
                all_founders.append(f)
    except Exception as e:
        print(f"Velocity scout error: {e}")

    # 3. Contributors to Hot Projects
    try:
        contributor = ContributorScout(token)
        for f in contributor.get_hot_project_contributors():
            if f['username'] not in seen_usernames:
                seen_usernames.add(f['username'])
                all_founders.append(f)
    except Exception as e:
        print(f"Contributor scout error: {e}")

    # 4. Keyword Search
    try:
        keyword = KeywordScout(token)
        for f in keyword.search():
            if f['username'] not in seen_usernames:
                seen_usernames.add(f['username'])
                all_founders.append(f)
    except Exception as e:
        print(f"Keyword scout error: {e}")

    # 5. HuggingFace
    try:
        hf = HuggingFaceScout()
        for f in hf.search_indian_ml_builders():
            if f['username'] not in seen_usernames:
                seen_usernames.add(f['username'])
                all_founders.append(f)
    except Exception as e:
        print(f"HuggingFace scout error: {e}")

    # Calculate scores and sort
    all_founders = [calculate_score(f) for f in all_founders]
    all_founders.sort(key=lambda x: x['overall_score'], reverse=True)

    # Prepare output
    output = []
    for f in all_founders:
        output.append({
            'name': f.get('name', ''),
            'username': f.get('username', ''),
            'bio': f.get('bio', ''),
            'location': f.get('location', ''),
            'avatar_url': f.get('avatar_url', ''),
            'html_url': f.get('html_url', ''),
            'followers': f.get('followers', 0),
            'public_repos': f.get('public_repos', 0),
            'company': f.get('company', ''),
            'blog': f.get('blog', ''),
            'twitter': f.get('twitter', ''),
            'discovery_method': f.get('discovery_method', ''),
            'trending_repo': f.get('trending_repo', ''),
            'contributed_to': f.get('contributed_to', ''),
            'scores': f.get('scores', {}),
            'overall_score': f.get('overall_score', 0),
            'source': 'huggingface' if f.get('discovery_method') == 'huggingface' else 'github'
        })

    # Save results
    with open('developers.json', 'w') as file:
        json.dump(output, file, indent=2)

    print(f"\nFound {len(output)} founders!")
    print(f"   - Trending: {len([f for f in all_founders if f.get('discovery_method') == 'trending'])}")
    print(f"   - Star Velocity: {len([f for f in all_founders if f.get('discovery_method') == 'star_velocity'])}")
    print(f"   - Contributors: {len([f for f in all_founders if f.get('discovery_method') == 'contributor'])}")
    print(f"   - Keyword: {len([f for f in all_founders if f.get('discovery_method') == 'keyword'])}")
    print(f"   - HuggingFace: {len([f for f in all_founders if f.get('discovery_method') == 'huggingface'])}")
    print("=" * 50)


if __name__ == '__main__':
    main()
