import argparse
import time

from src.get_tool_env import get_env_from_requirements
from src.utils import get_galaxy_instance, user_is_admin
from src.test import run_tool_test
from src.delete_histories import delete_histories
from src.conda_commands import print_conda_commands
from src.mulled_hash import mulled_hash

from src.get_tool_reqs import get_requirement_str_for_tool_id

from src.command_line import command_line_parser
# reload
# delete-histories
# test
# conda-commands

def main():
    parser = command_line_parser()
    # parser = argparse.ArgumentParser(description='Search for tools on Galaxy using repository name or tool display name')
    # parser.add_argument('action', help='find, show-requirements')
    # parser.add_argument('-n', '--name', help='Tool repository name')
    # parser.add_argument('-N', '--display_name', help='User facing tool name')
    # parser.add_argument('-v', '--version', help='Version')
    # parser.add_argument('-o', '--owner', nargs='+', help='Show tools from one or more owners')
    # parser.add_argument('-z', '--fuzz', action='store_true', help='Match substring of repository name from search term')
    # parser.add_argument('--all', help='Show all installed tools', action='store_true')
    # parser.add_argument('-e', '--env', help='Show virtual environment name (admin API key required)', action='store_true')
    # parser.add_argument('-b', '--biotools', help='Show bio.tools IDs in output', action='store_true')  
    # parser.add_argument('-g', '--galaxy_url', help='URL of Galaxy instance')
    # parser.add_argument('-a', '--api_key', help='Galaxy api key')
    # parser.add_argument('-p', '--profile', help='Key for profile set in profiles.yml')
    # parser.add_argument('-t', '--tool_ids', nargs='+', help='One or more tool ids to match exactly')
    # parser.add_argument('--tags', nargs='+', help='Tags for test history')
    # parser.add_argument('-s', '--sleep', action='store_true', help='Sleep for 0.5s after fetching requirements')

    args = parser.parse_args()

    if not hasattr(args, 'action'):  # hackily default to find. There has to  be a better way
        args.action = 'find'
        args.require_galaxy = True
        args.require_login = False
        args.require_admin = False
        print(dir(args))

    if args.require_galaxy:
        galaxy_instance = get_galaxy_instance(args.galaxy_url, args.api_key, args.profile)
 
    if args.require_login:
        if not galaxy_instance.key:
            print(f'Login required for {args.action} action')
            return

    if args.require_admin:
        if not user_is_admin(galaxy_instance):
            print(f'Non-admin accounts cannot perform this action: {args.action}')
            return

    # if args.action == 'show-requirements':
    #     print(get_requirement_str_for_tool_id(galaxy_instance, args.tool_ids[0], False))
    #     return

    if args.action == 'test':
        run_tool_test(galaxy_instance, args.tool_ids[0], tags=args.tags)
        return

    if args.action == 'delete-histories':
        delete_histories(galaxy_instance, args)
        return

    if args.action == 'find':
        get_tool_details(galaxy_instance, args)
        return

    if args.action == 'conda-commands':
        print_conda_commands(galaxy_instance, args)
        return

    if args.action == 'mulled-hash':
        mulled_hash(args)
        return

    # if args.action == 'delete-histories':
    #     delete_histories(galaxy_instance, args.tool_ids[0], tags=args.tags)
    #     return

def get_tool_details(galaxy_instance, args):

    name = args.name
    display_name = args.display_name
    version = args.version
    owner = args.owner
    fuzz = args.fuzz
    tool_ids = args.tool_ids
    env = args.env
    biotools = args.biotools
    all = args.all

    tools = [t for t in galaxy_instance.tools.get_tools()]  # shed tools only.  # TODO: allow non-shed-tools to be returned here

    if not all and not tool_ids:
        if not (name or display_name or owner):
            print('either name, display_name or owner must be specified')
            return
        if name and not fuzz:
            tools = [t for t in tools if t.get('tool_shed_repository') and t['tool_shed_repository']['name'] == name]
        if name and fuzz:
            tools = [t for t in tools if t.get('tool_shed_repository') and name in t['tool_shed_repository']['name']]
        if display_name:
            tools = [t for t in tools if display_name.lower() in t['name'].lower()]
        if version:
            tools = [t for t in tools if version in t['version']]
        if owner:
            tools = [t for t in tools if t.get('tool_shed_repository') and t['tool_shed_repository']['owner'] in owner]
    elif tool_ids:
        tools = [t for t in tools if t['id'] in tool_ids]
    if not tools:
        print('No tools found')
        return
    include_env = user_is_admin(galaxy_instance) and env

    def get_row(tool):
        row = [
            tool['name'],
            tool['tool_shed_repository']['name'] if tool.get('tool_shed_repository') else '-',
            tool['tool_shed_repository']['owner'] if tool.get('tool_shed_repository') else '-',
            tool['tool_shed_repository']['changeset_revision'] if tool.get('tool_shed_repository') else '-',
            tool['version'],
            tool['panel_section_name'],
            tool['id'],
        ]
        if include_env:
            row.append(get_env_from_requirements(galaxy_instance.tools.requirements(tool['id'])) or '-')
            if args.sleep:
                time.sleep(0.5)
        if biotools:
            xrefs = tool.get('xrefs')
            biotools_ids = [x['value'] for x in xrefs if x['reftype'] == 'bio.tools']
            row.append(' '.join(biotools_ids) if biotools_ids else '-')
        return row
    
    header = ['Display Name', 'Repo name', 'Owner', 'Revision', 'Version', 'Section Label', 'Tool ID']
    if biotools:
        header.append('Biotools ID')
    if include_env:
        header.append('Environment')
    rows = [get_row(tool) for tool in tools]
 
    print('\t'.join(header))
    for row in rows:
        print('\t'.join([str(r) for r in row]))


if __name__ == "__main__":
    main()
