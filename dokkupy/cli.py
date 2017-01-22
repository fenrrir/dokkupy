import argparse
import dokkupy


def main():
    parser = argparse.ArgumentParser(description='Deploy on dokku with dokkupy')
    parser.add_argument('--project-name', required=True, help='project name')
    parser.add_argument('--address', required=True, help='address of dokku instance')
    parser.add_argument('--config', required=True, help='config file')
    parser.add_argument('command', choices=['deploy', 'remove'])

    args = parser.parse_args()

    dokku = dokkupy.Dokku(args.address)
    if args.command == 'deploy':
        dokku.deploy_from_file(args.project_name, args.config)
    else:
        dokku.remove_from_file(args.project_name, args.config)


if __name__ == '__main__':
    main()
