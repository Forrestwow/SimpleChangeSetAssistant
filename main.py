import configparser
import asyncio
import json
from sf.action import SF
from file_reader.csv_reader import CsvFile


async def main():
    # TODO Use JSON file instead of ini file
    config = configparser.ConfigParser()
    config.read('sf_config.ini')

    cmps = load_components(config)

    sf_assistant = SF(config)
    await sf_assistant.init()
    await sf_assistant.login()
    await sf_assistant.goto_change_set()
    await sf_assistant.new_change_set(config['ChangeSet']['SetName'])
    await sf_assistant.add_change_set_components(cmps)
    await asyncio.sleep(5)
    await sf_assistant.close()

def load_components(config):
    csv_file = CsvFile()

    components = csv_file \
        .source(config['ChangeSet']['FilePath']) \
        .select(json.loads(config['ChangeSet']['SelectFilter'])) \
        .collect()
    return components

if __name__ == '__main__':
    asyncio.run(main())