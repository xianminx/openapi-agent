import json
import logging
from typing import Any, Dict, Optional

import requests
from swarm.types import Agent, AgentFunction, Result

from .openapi_spec import OpenAPISpec, OpenAPISpecError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class OpenAPIAgent(Agent):
    """
    OpenAPIAgent is a class that interacts with OpenAPI-based services.
    
    This agent is capable of loading OpenAPI specifications, routing requests to appropriate
    endpoints, and making API calls. It also handles authentication if an auth class is provided.

    Attributes:
        auth: An optional authentication class instance.
        openapi_spec: An OpenAPISpec instance containing the loaded API specification.
        instructions: A string containing instructions for the agent.
        functions: A list of AgentFunction instances available to the agent.

    Args:
        spec_path (str): The path to the OpenAPI specification file.
        model (str): The name of the model to use for the agent. Defaults to 'gpt-4o-mini'.
        auth_class (optional): A class to handle authentication. Defaults to None.
        name (str, optional): The name of the agent. Defaults to "OpenAPI Agent".
    """

    class Config:
        extra = 'allow'

    def __init__(self, spec_path: str, model='gpt-4o-mini', auth_class=None, name: str = "OpenAPI Agent"):
        super().__init__(name=name, model=model)
        self.auth = auth_class() if auth_class else None
        self.openapi_spec = self._load_openapi_spec(spec_path)
        self.instructions = self._get_instructions()
        self.functions = [self.find_api_details, self.call_api]
        logger.info(f"Initialized {name} with spec from {spec_path} using model {model}")

    def _load_openapi_spec(self, spec_path: str) -> OpenAPISpec:
        """
        Load the OpenAPI specification from the given path.

        Args:
            spec_path (str): The path to the OpenAPI specification file.

        Returns:
            OpenAPISpec: An instance of OpenAPISpec containing the loaded specification.

        Raises:
            OpenAPISpecError: If there's an error loading the specification.
        """
        try:
            spec = OpenAPISpec(spec_path)
            logger.info(f"Successfully loaded OpenAPI specification from {spec_path}")
            return spec
        except OpenAPISpecError as e:
            logger.error(f"Failed to load OpenAPI specification from {spec_path}: {str(e)}")
            raise

    def _get_instructions(self) -> str:
        """
        Generate instructions for the agent based on the loaded OpenAPI specification.

        Returns:
            str: A string containing instructions for the agent.
        """
        paths = self.openapi_spec.get_all_paths()
        paths_summary = "\n".join([f"- {method.upper()} {path}: {summary}" for method, path, summary in paths])

        return f"""
        You are an intelligent OpenAPI router agent for a service. Your primary task is to interpret user requests and map them to the most appropriate API endpoint and method.

        Available API endpoints:

        {paths_summary}

        Instructions:
        1. Carefully analyze the user's request to understand their intent.
        2. Match the request to the most suitable API endpoint and HTTP method.
        3. If multiple endpoints seem relevant, choose the most specific one.
        4. If no matching API is found, respond with "No matching API found" and suggest alternatives if possible.
        5. If the request lacks necessary details for the API call:
           a. Use the find_api_details function with the chosen method and path to get the API specification.
           b. Inform the user about the required parameters and their constraints.
        6. Once you have all required information:
           a. Use the call_api function with the appropriate method, path, and parameters to execute the API call.
           b. Provide a concise summary of the API response to the user.

        Remember:
        - Always prioritize using the API endpoints over providing information directly.
        - Ensure all required parameters are collected before making an API call.
        - If an API call fails, provide a clear explanation to the user and suggest next steps.

        Your responses should be helpful, concise, and focused on facilitating successful API interactions.
        """

    def get_auth_token(self) -> Optional[str]:
        """
        Get the authentication token if an auth class is provided.

        Returns:
            Optional[str]: The authentication token if available, None otherwise.
        """
        if self.auth:
            logger.debug("Attempting to get auth token")
            try:
                token = self.auth.authenticate()['access_token']
                logger.info("Successfully obtained auth token")
                return token
            except Exception as e:
                logger.error(f"Failed to obtain auth token: {str(e)}")
                return None
        logger.debug("No auth class provided, skipping authentication")
        return None

    def find_api_details(self, method: str, path: str) -> str:
        """
        Find and return the API details for a given method and path.

        Args:
            method (str): The HTTP method (e.g., GET, POST, PUT, DELETE).
            path (str): The API endpoint path.

        Returns:
            str: A formatted string containing the API details.
        """
        logger.info(f"Routing request to: {method} {path}")
        api_details = self.openapi_spec.get_api_details(path, method)

        if not api_details:
            return f"No API details found for {method.upper()} {path}"

        formatted_details = json.dumps(api_details, indent=2)
        return f"""
        Here is the specification for the API call:

        {method.upper()} {path}

        ```json
        {formatted_details}
        ```

        Important:
        - Ensure all required parameters are provided.
        - Adhere to the parameter types and constraints specified above.
        - The request body should match the schema provided (if applicable).
        - Be prepared to handle the possible response codes and their content.
        """

    def call_api(self, endpoint: str, params: Dict[str, Any] = None, method: str = 'GET', data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make an API call to the specified endpoint.

        Args:
            endpoint (str): The API endpoint to call.
            params (Dict[str, Any], optional): Query parameters for the API call. Defaults to None.
            method (str, optional): The HTTP method to use. Defaults to 'GET'.
            data (Dict[str, Any], optional): The request body for POST/PUT requests. Defaults to None.

        Returns:
            Dict[str, Any]: The API response as a dictionary.
        """
        logger.info(f"Initiating API call: {method} {endpoint}")
        token = self.get_auth_token()
        base_url = self.openapi_spec.spec.get('servers', [{}])[0].get('url', '')
        url = f"{base_url}/{endpoint.lstrip('/')}"

        headers = {"Authorization": f"Bearer {token}"} if token else {}

        try:
            response = self._make_request(method, url, headers, params, data)
            return self._handle_response(response, method, endpoint)
        except requests.RequestException as e:
            error_message = f"API call failed: {method} {endpoint}"
            logger.error(f"{error_message}. Error: {str(e)}")
            return {"error": error_message, "details": str(e)}

    def _make_request(self, method: str, url: str, headers: Dict[str, str], params: Dict[str, Any], data: Dict[str, Any]) -> requests.Response:
        """
        Make an HTTP request and handle token refresh if needed.

        Args:
            method (str): The HTTP method to use.
            url (str): The full URL for the API call.
            headers (Dict[str, str]): The request headers.
            params (Dict[str, Any]): Query parameters for the API call.
            data (Dict[str, Any]): The request body for POST/PUT requests.

        Returns:
            requests.Response: The HTTP response object.
        """
        logger.debug(f"Making request to {url} with params: {params} and data: {data}")
        response = requests.request(method, url, headers=headers, params=params, json=data)

        if response.status_code == 401 and self.auth:
            logger.warning("Received 401 Unauthorized, attempting to refresh token")
            new_token = self.get_auth_token()  # This will refresh the token if needed
            headers["Authorization"] = f"Bearer {new_token}"
            logger.info("Retrying request with new token")
            response = requests.request(method, url, headers=headers, params=params, json=data)

        return response

    def _handle_response(self, response: requests.Response, method: str, endpoint: str) -> Dict[str, Any]:
        """
        Handle the API response.

        Args:
            response (requests.Response): The HTTP response object.
            method (str): The HTTP method used for the request.
            endpoint (str): The API endpoint called.

        Returns:
            Dict[str, Any]: The processed API response as a dictionary.
        """
        if response.ok:
            logger.info(f"API call successful: {method} {endpoint} (Status: {response.status_code})")
            return response.json() if response.text else None
        else:
            error_message = f"API call failed: {method} {endpoint} (Status: {response.status_code})"
            logger.error(f"{error_message}. Error details: {response.text}")
            return {"error": error_message, "details": response.text}
