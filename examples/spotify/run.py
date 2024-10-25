import logging
import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from swarm.repl import run_demo_loop
from openapi_agent.agent_v2 import OpenAPIAgent
from examples.spotify.auth import SpotifyAuth

logger = logging.getLogger(__name__)

def main():
    logger.setLevel(logging.DEBUG)

    # Initialize the OpenAPIAgent for Spotify
    current_dir = os.path.dirname(__file__)
    spec_path = os.path.join(current_dir, 'spec/fixed-spotify-open-api.yml')
    spotify_agent = OpenAPIAgent(
        spec_path, auth_class=SpotifyAuth, name="Spotify Agent")

    # Run the demo loop
    run_demo_loop(
        starting_agent=spotify_agent,
        context_variables={},
        stream=True,
        debug=False
    )

if __name__ == "__main__":
    main()
