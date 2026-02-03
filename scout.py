#!/usr/bin/env python3
"""
Founder Scout - India Focus (GitHub + Hugging Face)
Implements Antler's dual-platform scouting strategy.
"""

import requests
import json
import time
import os
from datetime import datetime, timedelta


class GitHubScout:
    """GitHub scouting with Antler's search queries"""

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'

        self.corporate_keywords = [
            '@google', '@microsoft', '@meta', '@amazon', '@apple',
            '@netflix', '@uber', '@stripe', '@shopify', '@oracle'
        ]

        self.india_keywords = [
            'india', 'bangalore', 'bengaluru', 'delhi', 'mumbai',
            'hyderabad', 'chennai', 'pune', 'kolkata', 'gurgaon',
            'noida', 'ahmedabad', 'jaipur', 'mysuru', 'rajasthan'
        ]

        self.pioneer_keywords = [
            'agentic', 'langchain', 'langgraph', 'pydantic-ai', 'mcp',
            'rag', 'llm', 'gpt', 'transformer', 'embedding', 'vector',
            'claude', 'openai', 'anthropic', 'fine-tuning', 'llama'
        ]

        self.founder_signals = [
            'founder', 'co-founder', 'cto', 'ceo', 'building',
            'creator', 'indie', 'bootstrapped', 'maker'
        ]

    def _request(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            time.sleep(60)
            return self._request(endpoint, params)
        return None

    def search_founders(self, max_users: int = 50) -> list:
        """Execute Antler's GitHub scouting strategy"""
        developers = {}

        # ANTLER SCOUTING QUERIES
        searches = [
            '"Founder" "Building" "agentic" location:India',
            '"Co-founder" OR "CTO" "Agentic" location:India',
            '"Building" "langgraph" location:India',
            '"Founder" "langchain" location:India',
            '"Founder" OR "CTO" "LLM" location:India',
            '"Stealth" AND "agentic" location:India',
            'location:india followers:>100 repos:>10',
            'location:bangalore followers:>50 "founder"',
            'location:india language:python "llm"',
            'location:india language:python "langchain"',
        ]

        print("GitHub Scouting...")
        for query in searches:
            result = self._request('/search/users', {
                'q': query, 'sort': 'followers', 'per_page': 30
            })
            if result and 'items' in result:
                for user in result['items']:
                    developers[user['login']] = user
            time.sleep(2)

        print(f"Found {len(developers)} potential founders")
        return self._enrich_users(list(developers.values())[:max_users])

    def _enrich_users(self, users: list) -> list:
        enriched = []
        for user in users:
            user_data = self._request(f"/users/{user['login']}")
            if not user_data or not self._is_india(user_data.get('location', '')):
                continue

            repos = self._request(f"/users/{user['login']}/repos", {'per_page': 30}) or []
            scores = self._calculate_scores(user_data, repos)

            enriched.append({
                'username': user_data['login'],
                'name': user_data.get('name') or user_data['login'],
                'bio': (user_data.get('bio') or '')[:200],
                'location': user_data.get('location', 'India'),
                'followers': user_data.get('followers', 0),
                'public_repos': user_data.get('public_repos', 0),
                'avatar_url': user_data.get('avatar_url', ''),
                'html_url': user_data.get('html_url', ''),
                'source': 'github',
                'top_repos': self._get_top_repos(repos),
                'languages': self._get_languages(repos),
                **scores
            })
            time.sleep(1)

        return sorted(enriched, key=lambda x: x['overall_score'], reverse=True)

    def _is_india(self, location: str) -> bool:
        if not location:
            return False
        return any(kw in location.lower() for kw in self.india_keywords)

    def _calculate_scores(self, user: dict, repos: list) -> dict:
        total_stars = sum(r.get('stargazers_count', 0) for r in repos)

        try:
            created = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
            days = max(1, (datetime.now(created.tzinfo) - created).days)
            growth = min(100, (total_stars / days) * 50)
        except:
            growth = 50

        cutoff = (datetime.now() - timedelta(days=90)).isoformat()
        recent = len([r for r in repos if r.get('pushed_at', '') > cutoff])
        velocity = min(100, recent * 20)

        followers = max(1, user.get('followers', 1))
        undervalued = min(100, ((total_stars + len(repos) * 5) / followers) * 15)

        pioneer = 0
        for repo in repos[:10]:
            desc = (repo.get('description') or '').lower()
            topics = ' '.join(repo.get('topics', []))
            if any(kw in f"{desc} {topics}" for kw in self.pioneer_keywords):
                pioneer += 15
        pioneer = min(100, pioneer)

        overall = growth * 0.2 + velocity * 0.3 + undervalued * 0.25 + pioneer * 0.25

        return {
            'total_stars': total_stars,
            'growth_score': round(growth),
            'velocity_score': round(velocity),
            'undervalued_score': round(undervalued),
            'pioneer_score': round(pioneer),
            'overall_score': round(overall, 1)
        }

    def _get_top_repos(self, repos: list) -> list:
        sorted_repos = sorted(repos, key=lambda r: r.get('stargazers_count', 0), reverse=True)
        return [{
            'name': r['name'],
            'description': (r.get('description') or '')[:150],
            'stars': r.get('stargazers_count', 0),
            'language': r.get('language'),
            'url': r.get('html_url'),
            'topics': r.get('topics', [])[:5]
        } for r in sorted_repos[:3] if not r.get('fork')]

    def _get_languages(self, repos: list) -> list:
        langs = {}
        for r in repos:
            if r.get('language'):
                langs[r['language']] = langs.get(r['language'], 0) + 1
        return sorted(langs.items(), key=lambda x: x[1], reverse=True)[:5]


class HuggingFaceScout:
    """Hugging Face scouting for ML builders"""

    def __init__(self):
        self.base_url = 'https://huggingface.co/api'

    def search_indian_ml_builders(self, max_users: int = 20) -> list:
        print("HuggingFace Scouting...")
        builders = []

        for term in ['india', 'indian', 'hindi', 'indic']:
            try:
                response = requests.get(f"{self.base_url}/models", params={'search': term, 'limit': 50})
                if response.status_code == 200:
                    for model in response.json():
                        author = model.get('author', '')
                        if author and author not in [b.get('username') for b in builders]:
                            info = self._get_author_info(author, model)
                            if info:
                                builders.append(info)
                time.sleep(1)
            except:
                pass

        print(f"Found {len(builders)} HuggingFace builders")
        return builders[:max_users]

    def _get_author_info(self, username: str, model: dict) -> dict:
        try:
            models_resp = requests.get(f"{self.base_url}/models", params={'author': username})
            models = models_resp.json() if models_resp.status_code == 200 else []

            if len(models) < 2:
                return None

            total_downloads = sum(m.get('downloads', 0) for m in models)
            total_likes = sum(m.get('likes', 0) for m in models)

            growth = min(100, (total_downloads / 1000) * 10)
            velocity = min(100, len(models) * 15)
            undervalued = min(100, (total_downloads / max(1, total_likes)) * 5)
            pioneer = min(100, len(models) * 10)
            overall = (growth + velocity + undervalued + pioneer) / 4

            return {
                'username': username,
                'name': username,
                'bio': f"ML Builder - {len(models)} models on HuggingFace",
                'location': 'India',
                'followers': total_likes,
                'public_repos': len(models),
                'avatar_url': f"https://huggingface.co/avatars/{username}",
                'html_url': f"https://huggingface.co/{username}",
                'source': 'huggingface',
                'total_stars': total_downloads,
                'growth_score': round(growth),
                'velocity_score': round(velocity),
                'undervalued_score': round(undervalued),
                'pioneer_score': round(pioneer),
                'overall_score': round(overall, 1),
                'top_repos': [{
                    'name': m.get('id', '').split('/')[-1],
                    'description': f"Downloads: {m.get('downloads', 0):,}",
                    'stars': m.get('downloads', 0),
                    'language': 'Python',
                    'url': f"https://huggingface.co/{m.get('id', '')}",
                    'topics': m.get('tags', [])[:5]
                } for m in models[:3]],
                'languages': [['Python', len(models)]]
            }
        except:
            return None


def main():
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("GITHUB_TOKEN not set")
        return

    all_founders = []

    github_scout = GitHubScout(token)
    github_founders = github_scout.search_founders(max_users=30)
    all_founders.extend(github_founders)

    hf_scout = HuggingFaceScout()
    hf_founders = hf_scout.search_indian_ml_builders(max_users=10)
    all_founders.extend(hf_founders)

    all_founders.sort(key=lambda x: x['overall_score'], reverse=True)

    with open('developers.json', 'w') as f:
        json.dump(all_founders, f, indent=2)

    print(f"Saved {len(all_founders)} founders (GitHub: {len(github_founders)}, HF: {len(hf_founders)})")


if __name__ == '__main__':
    main()
