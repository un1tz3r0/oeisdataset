import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import logging
import json
import os

async def fetch_sequence_page(session: aiohttp.ClientSession, oeis_id: str, retries=3, timeout_duration=10):
    """Fetches a single OEIS sequence page and extracts the sequence.

    Args:
        session: The aiohttp ClientSession.
        oeis_id: The OEIS ID (e.g., "A000045").
        retries: Number of retries if a request fails.
        timeout_duration: timeout duration in seconds.
    Returns:
        A list of integers representing the sequence, or None if an error occurred.
        Also returns the OEIS ID, for tracking.  Returns (None, oeis_id) on failure.
    """
    url = f"https://oeis.org/{oeis_id}"
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=timeout_duration) as response:
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                html = await response.text()

                soup = BeautifulSoup(html, 'html.parser')

                # Find the sequence data. This is the most robust method,
                # handling different OEIS page formats.
                sequence_element = soup.find('tt')
                if sequence_element:
                    sequence_text = sequence_element.get_text()
                    # Use regular expression to extract numbers, handling commas, spaces and newlines.
                    sequence = [int(num) for num in re.findall(r'-?\d+', sequence_text)]
                    return sequence, oeis_id
                else:
                    logging.warning(f"Could not find sequence data for {oeis_id}")
                    return None, oeis_id

        except aiohttp.ClientResponseError as e:
            logging.warning(f"HTTP error for {oeis_id} (attempt {attempt+1}/{retries}): {e}")
            if e.status == 404:
                #If it is not found, there is no point in retrying
                return None, oeis_id
            await asyncio.sleep(2**(attempt+1))  # Exponential backoff
        except aiohttp.ClientError as e:  # Catch broader aiohttp errors
            logging.warning(f"Client error for {oeis_id} (attempt {attempt+1}/{retries}): {e}")
            await asyncio.sleep(2**(attempt+1))
        except asyncio.TimeoutError:
            logging.warning(f"Timeout for {oeis_id} (attempt {attempt + 1}/{retries})")
            await asyncio.sleep(2 ** (attempt + 1))
        except Exception as e:
            logging.exception(f"Unexpected error for {oeis_id} (attempt {attempt+1}/{retries}): {e}")
            await asyncio.sleep(2**(attempt+1))

    logging.error(f"Failed to fetch {oeis_id} after {retries} attempts.")
    return None, oeis_id


async def process_oeis_range(start_id: int, end_id: int, output_file: str = "oeis_data.jsonl", batch_size: int = 50, resume: bool = True):
    """Fetches a range of OEIS sequences and saves them to a JSON Lines file.

    Args:
        start_id: The starting OEIS ID (inclusive, e.g., 1 for A000001).
        end_id: The ending OEIS ID (inclusive).
        output_file: Path to the output JSON Lines file.
        batch_size: Number of sequences to fetch concurrently.
        resume: Whether to resume from a previous run.
    """

    # Create or load the index file
    index_file = "oeis_index.json"
    if resume and os.path.exists(index_file):
        with open(index_file, "r") as f:
            index = json.load(f)
    else:
        index = {"processed": []}


    processed_ids = set(index["processed"])

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(start_id, end_id + 1):
            oeis_id = f"A{i:06}"  # Format the ID correctly (e.g., A000001)

            if oeis_id in processed_ids:
              logging.info(f"Skipping {oeis_id} (already processed)")
              continue

            task = asyncio.create_task(fetch_sequence_page(session, oeis_id))
            tasks.append(task)

            if len(tasks) >= batch_size:
                results = await asyncio.gather(*tasks)
                save_results(results, output_file, index, index_file)
                tasks = []  # Clear the task list

        # Process any remaining tasks
        if tasks:
            results = await asyncio.gather(*tasks)
            save_results(results, output_file, index, index_file)


def save_results(results, output_file, index, index_file):
    """Saves the fetched sequences to the output file and updates the index."""

    with open(output_file, "a") as f:
        for sequence, oeis_id in results:
            if sequence:
                data = {"id": oeis_id, "sequence": sequence}
                f.write(json.dumps(data) + "\n")
            if oeis_id:  # Mark as processed even on failure
                index["processed"].append(oeis_id)

    # Save index
    with open(index_file, "w") as f:
        json.dump(index, f)

def setup_logging(log_level=logging.INFO):
  """Sets up logging with the specified log level."""
  logging.basicConfig(
      level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
  )

async def main():
    """Main function to run the scraper."""
    setup_logging()

    start_id = 1  # Start from A000001
    end_id = 368000 # Current Maximum Number of entries.
    #  (You should adjust this - a smaller range is recommended for testing!)
    #  For example:
    #  start_id = 1
    #  end_id = 100
    #  The OEIS has over 360,000 entries; fetching them all will take *days*.
    #  It will also generate *gigabytes* of data.

    output_file = "oeis_data.jsonl"  # Use JSON Lines format
    batch_size = 100  # Adjust for concurrency (higher = faster, but more load)
    resume = True  # Set to False to start fresh, True to resume

    await process_oeis_range(start_id, end_id, output_file, batch_size, resume)
    print("Scraping complete.")



if __name__ == "__main__":
    asyncio.run(main())
