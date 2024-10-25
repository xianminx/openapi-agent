import json
import os
from typing import Any, Dict, List, Tuple, Optional
import urllib.request

import yaml

class OpenAPISpecError(Exception):
    """Custom exception for OpenAPISpec errors."""
    pass

class OpenAPISpec:
    """
    A class for parsing and interacting with OpenAPI specifications.

    This class provides methods to load an OpenAPI specification from a YAML file or a remote URI,
    resolve references within the specification, and extract various details from it.

    Attributes:
        spec (Dict[str, Any]): The loaded OpenAPI specification.

    Methods:
        load_openapi_spec: Load the OpenAPI specification from a YAML file or remote URI.
        get_all_paths: Get all paths and their summaries from the specification.
        get_api_details: Get detailed information about a specific API endpoint.
    """

    def __init__(self, source: str):
        """
        Initialize the OpenAPISpec with a specification file or remote URI.

        Args:
            source (str): The path to the OpenAPI specification YAML file or a remote URI.

        Raises:
            OpenAPISpecError: If the specification cannot be loaded or parsed.
        """
        try:
            self.spec = self.load_openapi_spec(source)
        except Exception as e:
            raise OpenAPISpecError(f"Failed to load OpenAPI specification: {str(e)}") from e

    @staticmethod
    def load_openapi_spec(source: str) -> Dict[str, Any]:
        """
        Load the OpenAPI specification from a YAML file or remote URI.

        Args:
            source (str): The path to the OpenAPI specification YAML file or a remote URI.

        Returns:
            Dict[str, Any]: The loaded OpenAPI specification as a dictionary.

        Raises:
            OpenAPISpecError: If the specification cannot be read or parsed.
        """
        try:
            if source.startswith(('http://', 'https://')):
                with urllib.request.urlopen(source) as response:
                    content = response.read().decode('utf-8')
                    return yaml.safe_load(content)
            else:
                with open(source, 'r') as file:
                    return yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise OpenAPISpecError(f"Error parsing YAML: {str(e)}") from e
        except (IOError, urllib.error.URLError) as e:
            raise OpenAPISpecError(f"Error reading from source: {str(e)}") from e

    def _resolve_ref(self, ref: str) -> Any:
        """
        Resolve a reference within the OpenAPI specification.

        Args:
            ref (str): The reference string to resolve.

        Returns:
            Any: The resolved reference.

        Raises:
            OpenAPISpecError: If the reference cannot be resolved.
        """
        parts = ref.split('/')
        current = self.spec
        try:
            for part in parts[1:]:  # Skip the first '#' part
                current = current[part]
            return current
        except KeyError as e:
            raise OpenAPISpecError(f"Failed to resolve reference '{ref}': {str(e)}") from e

    def _expand_refs(self, node: Any) -> Any:
        """
        Expand all references in a given node of the OpenAPI specification.

        Args:
            node (Any): The node to expand references in.

        Returns:
            Any: The node with all references expanded.
        """
        if isinstance(node, dict):
            new_node = {}
            for key, value in node.items():
                if key == '$ref':
                    return self._expand_refs(self._resolve_ref(value))
                else:
                    new_node[key] = self._expand_refs(value)
            return new_node
        elif isinstance(node, list):
            return [self._expand_refs(item) for item in node]
        else:
            return node

    def get_all_paths(self) -> List[Tuple[str, str, str]]:
        """
        Get all the paths and summaries from the OpenAPI specification.

        Returns:
            List[Tuple[str, str, str]]: A list of tuples containing:
                - HTTP method (e.g., 'GET', 'POST')
                - API path (e.g., '/me/albums')
                - Summary or description of the endpoint

        Raises:
            OpenAPISpecError: If the paths cannot be extracted from the specification.
        """
        try:
            paths = []
            for path, methods in self.spec['paths'].items():
                for method, details in methods.items():
                    summary = details.get('description') or details.get('summary', '')
                    paths.append((method.upper(), path, summary))
            return paths
        except KeyError as e:
            raise OpenAPISpecError(f"Failed to extract paths from specification: {str(e)}") from e

    def get_api_details(self, path: str, method: str, resolve_refs: bool = True, include_response: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get the API details for a given path and method, resolving all $refs.

        Args:
            path (str): The API path.
            method (str): The HTTP method.
            resolve_refs (bool, optional): If True, resolve all $refs in the API details. Defaults to True.
            include_response (bool, optional): If False, the 'responses' key will be removed from the returned dictionary. Defaults to False.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the API details, or None if the path/method combination is not found.

        Raises:
            OpenAPISpecError: If there's an error while processing the API details.
        """
        try:
            methods_dict = self.spec.get('paths', {}).get(path, {})
            api = next(
                (details for m, details in methods_dict.items() if m.lower() == method.lower()),
                None
            )
            if api is None:
                return None

            if resolve_refs:
                api = self._expand_refs(api)
            if not include_response:
                api.pop('responses', None)
            return api
        except Exception as e:
            raise OpenAPISpecError(f"Error processing API details for {method.upper()} {path}: {str(e)}") from e

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    yml_file_path = os.path.join(current_dir, 'fixed-spotify-open-api.yml')
    
    try:
        # Load from local file
        spec_local = OpenAPISpec(yml_file_path)
        print("Loaded specification from local file:")
        print(json.dumps(spec_local.get_all_paths()[:5], indent=2))  # Print first 5 paths

        albums_api = spec_local.get_api_details('/me/albums', 'get')
        print("\nAPI details for '/me/albums' (GET):")
        print(json.dumps(albums_api, indent=2))

        # Load from remote URI (example)
        remote_uri = "https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/examples/v3.0/petstore.yaml"
        spec_remote = OpenAPISpec(remote_uri)
        print("\nLoaded specification from remote URI:")
        print(json.dumps(spec_remote.get_all_paths(), indent=2))

    except OpenAPISpecError as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
