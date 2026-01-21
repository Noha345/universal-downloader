import re
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError, clean_html, get_element_by_class
# This imports your bypass script
from megacloud import Megacloud 

class HiAnimeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:hianime|hianimes)\.(?:to|is|nz|bz|pe|cx|gs|do|cz)/(?:watch/)?(?P<slug>[^/?]+)(?:-\d+)?-(?P<playlist_id>\d+)(?:\?ep=(?P<episode_id>\d+))?$'

    def _real_extract(self, url):
        # 1. Setup
        mobj = self._match_valid_url(url)
        episode_id = mobj.group('episode_id')
        # Handle cases where URL doesn't have ?ep= (default to first/only)
        if not episode_id:
             # Logic to find episode ID if missing would go here, 
             # but for now let's assume the link has it or fail gracefully
             pass 

        self.base_url = re.match(r'https?://[^/]+', url).group(0)

        # 2. Get the AJAX Data (The API calls)
        # We need the server ID first
        servers_url = f'{self.base_url}/ajax/v2/episode/servers?episodeId={episode_id}'
        # NOTE: We simply download the JSON. The bypass happens deeper in Megacloud.
        servers_data = self._download_json(servers_url, episode_id, note='Fetching Server IDs')
        
        # 3. Find the "HD-1" or "Sub" server
        html = servers_data.get('html', '')
        # Simple regex to find the data-id for the server "HD-1" or "Sub"
        # This is a simplified search to keep the code robust
        server_id_match = re.search(r'data-id="(\d+)"[^>]*>(?:.*?)HD-1', html)
        if not server_id_match:
             # Try fallback to just the first data-id found
             server_id_match = re.search(r'data-id="(\d+)"', html)
        
        if not server_id_match:
            raise ExtractorError("Could not find a valid video server ID")
            
        server_id = server_id_match.group(1)

        # 4. Get the Sources (The encrypted link)
        sources_url = f'{self.base_url}/ajax/v2/episode/sources?id={server_id}'
        sources_data = self._download_json(sources_url, episode_id, note='Fetching Video Sources')
        
        embed_url = sources_data.get('link')
        if not embed_url:
            raise ExtractorError("No embed URL found")

        # 5. THE BYPASS (Using your megacloud.py)
        # This is where your new cloudscraper code kicks in
        print(f"Decrypting with Megacloud: {embed_url}")
        scraper = Megacloud(embed_url)
        data = scraper.extract() # This uses the cloudscraper logic

        # 6. Pass result back to yt-dlp
        formats = []
        for source in data.get('sources', []):
            file_url = source.get('file')
            if file_url and file_url.endswith('.m3u8'):
                formats.extend(self._extract_m3u8_formats(
                    file_url, episode_id, 'mp4', entry_protocol='m3u8_native', m3u8_id='hls'
                ))
        
        return {
            'id': episode_id,
            'title': f"HiAnime - {episode_id}",
            'formats': formats,
        }
