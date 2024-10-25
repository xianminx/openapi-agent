import json
import logging
from typing import Any, Dict, Optional

import requests
from .openapi_spec import OpenAPISpec, OpenAPISpecError

from swarm.types import Agent, AgentFunction, Result

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
        model (str): The name of the model to use for the agent.
        auth_class (optional): A class to handle authentication. Defaults to None.
        name (str, optional): The name of the agent. Defaults to "OpenAPI Agent".
    """

    class Config:
        extra = 'allow'

    def __init__(self, spec_path: str, model: str, auth_class=None, name="OpenAPI Agent"):
        super().__init__(name=name, model=model)
        self.auth = auth_class() if auth_class else None
        self.openapi_spec = self._load_openapi_spec(spec_path)
        self.api_caller_agent = self._create_api_caller_agent()
        self.instructions = self._get_instructions()
        self.functions = [self.route_request]
        logger.info(f"Initialized {name} with spec from {spec_path} using model {model}")

    # ... (rest of the methods remain the same)
