import feedparser
import requests
import re
from pathlib import Path
from typing import Dict, Optional, List
import logging
from urllib.parse import urlparse, parse_qs

from config import config
from .utils import sanitize_filename

logger = logging.getLogger(__name__)


class ApplePodcastsHandler:
    """Handle Apple Podcasts download and metadata extraction"""

    def __init__(self):
        """Initialize Apple Podcasts handler"""
        self.temp_dir = config.TEMP_DIR
        self.itunes_lookup_api = "https://itunes.apple.com/lookup"

    def extract_podcast_id(self, url: str) -> Optional[str]:
        """
        Extract podcast ID from Apple Podcasts URL

        URL formats:
        - https://podcasts.apple.com/us/podcast/podcast-name/id1234567890
        - https://podcasts.apple.com/podcast/id1234567890

        Args:
            url: Apple Podcasts URL

        Returns:
            Podcast ID or None
        """
        # Try to find ID in URL
        match = re.search(r'/id(\d+)', url)
        if match:
            return match.group(1)

        logger.error(f"Could not extract podcast ID from URL: {url}")
        return None

    def get_podcast_info(self, podcast_id: str) -> Dict:
        """
        Get podcast information from iTunes API

        Args:
            podcast_id: Apple Podcasts ID

        Returns:
            Dictionary containing podcast information
        """
        try:
            params = {
                'id': podcast_id,
                'entity': 'podcast'
            }

            response = requests.get(self.itunes_lookup_api, params=params)
            response.raise_for_status()

            data = response.json()

            if data.get('resultCount', 0) == 0:
                raise ValueError(f"No podcast found with ID: {podcast_id}")

            result = data['results'][0]

            return {
                'id': podcast_id,
                'title': result.get('collectionName'),
                'artist': result.get('artistName'),
                'feed_url': result.get('feedUrl'),
                'genre': result.get('primaryGenreName'),
                'artwork_url': result.get('artworkUrl600'),
                'description': result.get('description', ''),
                'country': result.get('country'),
            }

        except Exception as e:
            logger.error(f"Failed to get podcast info: {e}")
            raise

    def get_rss_feed(self, feed_url: str) -> feedparser.FeedParserDict:
        """
        Parse RSS feed

        Args:
            feed_url: RSS feed URL

        Returns:
            Parsed feed object
        """
        try:
            logger.info(f"Fetching RSS feed: {feed_url}")
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                logger.warning(f"RSS feed has errors: {feed.bozo_exception}")

            return feed

        except Exception as e:
            logger.error(f"Failed to parse RSS feed: {e}")
            raise

    def get_episode_info(self, feed: feedparser.FeedParserDict, episode_index: int = 0) -> Dict:
        """
        Get specific episode information from feed

        Args:
            feed: Parsed RSS feed
            episode_index: Episode index (0 = latest)

        Returns:
            Dictionary containing episode information
        """
        try:
            if not feed.entries:
                raise ValueError("No episodes found in feed")

            if episode_index >= len(feed.entries):
                raise ValueError(f"Episode index {episode_index} out of range (total: {len(feed.entries)})")

            entry = feed.entries[episode_index]

            # Find audio enclosure
            audio_url = None
            audio_type = None
            audio_length = None

            for enclosure in entry.get('enclosures', []):
                if 'audio' in enclosure.get('type', ''):
                    audio_url = enclosure.get('href') or enclosure.get('url')
                    audio_type = enclosure.get('type')
                    audio_length = enclosure.get('length')
                    break

            # Try links if no enclosure found
            if not audio_url:
                for link in entry.get('links', []):
                    if 'audio' in link.get('type', ''):
                        audio_url = link.get('href')
                        break

            if not audio_url:
                raise ValueError(f"No audio URL found for episode: {entry.get('title')}")

            # Extract duration if available
            duration = None
            itunes_duration = entry.get('itunes_duration')
            if itunes_duration:
                # Parse duration (format: HH:MM:SS or MM:SS or seconds)
                try:
                    if ':' in itunes_duration:
                        parts = itunes_duration.split(':')
                        if len(parts) == 3:
                            duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                        elif len(parts) == 2:
                            duration = int(parts[0]) * 60 + int(parts[1])
                    else:
                        duration = int(itunes_duration)
                except:
                    pass

            return {
                'title': entry.get('title', 'Unknown Episode'),
                'description': entry.get('description', ''),
                'summary': entry.get('summary', ''),
                'published': entry.get('published', ''),
                'audio_url': audio_url,
                'audio_type': audio_type,
                'audio_length': audio_length,
                'duration': duration,
                'guid': entry.get('id') or entry.get('guid'),
            }

        except Exception as e:
            logger.error(f"Failed to get episode info: {e}")
            raise

    def get_all_episodes(self, feed: feedparser.FeedParserDict) -> List[Dict]:
        """
        Get all episodes from feed

        Args:
            feed: Parsed RSS feed

        Returns:
            List of episode information dictionaries
        """
        episodes = []

        for i in range(len(feed.entries)):
            try:
                episode_info = self.get_episode_info(feed, i)
                episodes.append(episode_info)
            except Exception as e:
                logger.warning(f"Skipping episode {i}: {e}")
                continue

        logger.info(f"Found {len(episodes)} episodes with audio")
        return episodes

    def download_audio(self, audio_url: str, filename: str) -> Path:
        """
        Download audio file from URL

        Args:
            audio_url: URL to audio file
            filename: Output filename (without extension)

        Returns:
            Path to downloaded audio file
        """
        try:
            # Sanitize filename
            safe_filename = sanitize_filename(filename)

            # Determine file extension from URL or content type
            extension = 'mp3'  # Default
            url_path = urlparse(audio_url).path
            if url_path:
                url_ext = Path(url_path).suffix.lstrip('.')
                if url_ext in ['mp3', 'm4a', 'mp4', 'wav']:
                    extension = url_ext

            output_file = self.temp_dir / f"{safe_filename}.{extension}"

            # Check if file already exists
            if output_file.exists():
                logger.info(f"Audio file already exists: {output_file}")
                return output_file

            logger.info(f"Downloading audio: {safe_filename}")

            # Download with streaming to handle large files
            response = requests.get(audio_url, stream=True)
            response.raise_for_status()

            # Update extension based on content type if available
            content_type = response.headers.get('content-type', '')
            if 'audio/mpeg' in content_type or 'audio/mp3' in content_type:
                extension = 'mp3'
            elif 'audio/mp4' in content_type or 'audio/m4a' in content_type:
                extension = 'm4a'

            output_file = self.temp_dir / f"{safe_filename}.{extension}"

            # Download file
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Progress indicator for large files
                        if total_size > 0 and downloaded % (1024 * 1024) == 0:  # Every MB
                            progress = (downloaded / total_size) * 100
                            logger.info(f"Download progress: {progress:.1f}%")

            logger.info(f"Audio downloaded: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Failed to download audio: {e}")
            raise


def process_apple_podcast_episode(url: str, episode_index: int = 0) -> Dict:
    """
    Process single Apple Podcasts episode

    Args:
        url: Apple Podcasts URL
        episode_index: Episode index (0 = latest)

    Returns:
        Dictionary containing episode information and file paths
    """
    handler = ApplePodcastsHandler()

    # Extract podcast ID
    podcast_id = handler.extract_podcast_id(url)
    if not podcast_id:
        raise ValueError("Could not extract podcast ID from URL")

    # Get podcast info
    podcast_info = handler.get_podcast_info(podcast_id)

    if not podcast_info.get('feed_url'):
        raise ValueError(f"No RSS feed URL found for podcast: {podcast_info.get('title')}")

    # Parse RSS feed
    feed = handler.get_rss_feed(podcast_info['feed_url'])

    # Get episode info
    episode_info = handler.get_episode_info(feed, episode_index)

    # Download audio
    filename = f"{podcast_info['title']}_{episode_info['title']}"
    audio_path = handler.download_audio(episode_info['audio_url'], filename)

    return {
        'podcast_info': podcast_info,
        'episode_info': episode_info,
        'audio_path': audio_path,
        'identifier': f"{podcast_id}_ep{episode_index}",
    }


def get_podcast_episodes(url: str) -> List[Dict]:
    """
    Get all episodes from an Apple Podcasts show

    Args:
        url: Apple Podcasts URL

    Returns:
        List of episode information dictionaries
    """
    handler = ApplePodcastsHandler()

    # Extract podcast ID
    podcast_id = handler.extract_podcast_id(url)
    if not podcast_id:
        raise ValueError("Could not extract podcast ID from URL")

    # Get podcast info
    podcast_info = handler.get_podcast_info(podcast_id)

    if not podcast_info.get('feed_url'):
        raise ValueError(f"No RSS feed URL found for podcast: {podcast_info.get('title')}")

    # Parse RSS feed
    feed = handler.get_rss_feed(podcast_info['feed_url'])

    # Get all episodes
    episodes = handler.get_all_episodes(feed)

    # Add podcast info to each episode
    for episode in episodes:
        episode['podcast_info'] = podcast_info
        episode['podcast_id'] = podcast_id

    return episodes
