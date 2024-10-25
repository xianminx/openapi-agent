from swarm.repl import run_demo_loop
from openapi_agent import OpenAPIAgent

def main():
    # Initialize the agent with an OpenAPI specification
    agent = OpenAPIAgent("path/to/openapi_spec.json")

    print("Welcome to the OpenAPI Agent! Tell me what you want to do.")
    run_demo_loop(agent)

if __name__ == "__main__":
    main()
