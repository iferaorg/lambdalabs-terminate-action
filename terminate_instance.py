"""Launch a Lambda Labs cloud instance from environment settings."""

import os
import sys
import time

import requests


def get_and_validate_env_vars():
    """Get and validate required environment variables."""
    instance_id = os.getenv("INSTANCE_ID")
    lambda_token = os.getenv("LAMBDA_TOKEN")

    if instance_id:
        instance_id = instance_id.split(",")
    else:
        raise ValueError("INSTANCE_ID environment variable is not set")

    instance_params = {
        "instance_ids": instance_id,
    }

    return instance_params, lambda_token


def launch_instance(instance_params, lambda_token):
    """Launch the instance and return the response."""
    url = "https://cloud.lambdalabs.com/api/v1/instance-operations/terminate"
    headers = {"Authorization": f"Bearer {lambda_token}"}

    response = requests.post(
        url,
        headers=headers,
        json=instance_params,
        timeout=300,
    )

    return response


def handle_response(response):
    """Handle the response from the instance launch."""
    if response.status_code != 200:
        error = response.json().get("error", {"message": "An unknown error occurred"})
        print(
            f'Error code: {response.status_code}, {error.get("code", "global/unknown")}'
            f'Message: {error["message"]}'
            f'Suggestion: {error.get("suggestion", "No suggestion available")}'
        )
        sys.exit(1)

    # Get data/instance_ids from response
    data = response.json().get("data", {})
    instance_id = data.get("instance_ids", [])[0]

    # Get the path to the GITHUB_OUTPUT environment file
    output_file_path = os.getenv("GITHUB_OUTPUT")

    # Write the output to the GITHUB_OUTPUT environment file
    if output_file_path is not None:
        with open(output_file_path, "a", encoding="utf-8") as file:
            file.write(f"instance_id={instance_id}\n")
    else:
        raise ValueError("GITHUB_OUTPUT environment variable is not set.")

    return instance_id


def wait_for_terminate(instance_id, lambda_token):
    """Wait for the instance to terminate."""
    if not os.getenv("WAIT_FOR_TERMINATE", "false").lower() == "false":
        return

    timeout = int(os.getenv("TERMINATE_TIMEOUT", "600"))
    start_time = time.time()
    url = f"https://cloud.lambdalabs.com/api/v1/instances/{instance_id}"
    headers = {"Authorization": f"Bearer {lambda_token}"}

    print("Waiting for instance to terminate...")

    while True:
        print('.', end='', flush=True)
        response = requests.get(url, headers=headers, timeout=10)
        instance_status = response.json().get("data", {}).get("status")
        if instance_status != "terminating":
            break
        if time.time() - start_time > timeout:
            raise TimeoutError("Instance terminate timeout reached.")
        time.sleep(5)  # Sleep for a short period before retrying

    # Status is now "terminated" or "unhealthy". Raise an error if unhealthy.
    if instance_status != "terminated":
        raise ValueError(f"Instance status is {instance_status}, expected 'terminated'.")

    total_time = time.time() - start_time
    print(f"\nInstance terminated in {total_time:.2f} seconds.")


def main():
    """Launch a Lambda Labs cloud instance from environment settings."""
    instance_params, lambda_token = get_and_validate_env_vars()
    response = launch_instance(instance_params, lambda_token)
    instance_id = handle_response(response)
    if instance_id:
        wait_for_terminate(instance_id, lambda_token)


if __name__ == "__main__":
    main()
