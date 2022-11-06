# HedgeDoc History Reference Generator

A wrapper around the hedgedoc cli binary to format the history based on the
given structure to create a reference page to other created notes.

## Why?

HedgeDoc works like Google Docs. You create a note and it generates a random ID,
but the catch is that it's only viewable in your own history, the problem is that
you can find your notes, but others can't, but this is only a problem if you're
collaborating and all of the notes you create need to be shared, it gets tiresome
pasting all of the links in one chat.

The problem is solved by just having the history in one note and other people can
just keep track of that. This should be used by a single user that opens other
links to have them in the history, otherwise this won't solve the problem.

## TODO

- [ ] Fix `upload-reference` command
  - `import` is not working due to error 409.
  - `delete` command doesn't work using the CLI.
- [ ] Add duplicate references for specific sections.
- [ ] Support `capitalize` for automatic section name capitalization.

## Requirements

- [HedgeDoc-CLI](http://github.com/hedgedoc/cli)
- Python 3.10+

## Setup

Using pip

```bash
# Activate virtualenv
pip install virtualenv
virtualenv venv --python 3.10
. venv/bin/activate

# Install the package
pip install -e .

hdd --help
```

Using Poetry

```bash
# Install the package
poetry install

poetry run hdd --help
```

## Environment variable file

Create a `.env` file in project root.

```conf
HD_USER=email@domain.com
HD_PASS=<PASS>
```

- This will be used to login using the hedgedoc cli.

## Usage

```bash
# Check history
hdd history

# Generate the markdown
hdd md
# Show the markdown, custom output and only pinned notes
hdd md --show --output ref.md --only-pinned

# Preview structure
hdd structure

# Upload the reference to HedgeDoc (not working now)
hdd upload-reference

# Enable TRACE logging
hdd --debug --log-level TRACE history

# Provide custom password 
hdd --username user --password pass history

```

## Reference Structure

By default if no sections are configured, everything is thrown under the "Uncategorized" section.

To define a structure, edit `hd.structure.yaml` or create a different file (but you would have to
specify the path every time)

To preview the structure run the following:

```bash
# With default config
hdd structure

# Custom config
hdd structure --structure path/to/structure.yaml
```


### Structure Examples

The structure is based on the document tags and if another tag is used in the previous section,
it will be removed and kept in the deeper level.

Simple structure

```yaml
tags:
  levels:
    security:
      - password-attacks
      - web-pentesting
    programming
```

- strings and dictionary keys are interpreted as the sections.
- You can have `programming:` with no value, it's supported.
- Everything under `levels` is interpreted as the reference structure.

To specify custom naming with explicit definitions:

- Explicit definitions are expected to have one of `tags`, `name`, `children`

```yaml
tags:
  levels:
    - tags: cybsec
      name: Cyber Security
      children:
        - password-attacks
        - web-pentesting
    - programming
```

Include multiple tags under one section:

```yaml
tags:
  levels:
    programming:
      - tags: [typescript, javascript, js, ts]
        name: JavaScript
```

Or use the second way:

```yaml
tags:
  levels:
    programming:
      - "#(typescript|javascript|js|ts)"  # No this is not a regex pattern.
        name: JavaScript
```

- This uses a special syntax that I can regex my way into and grab all the tags.

Complex structure with all of the syntax supported:

```yaml
tags:
  capitalize: true  # Currently not used.
  levels:
    - tags: [security]
      name: Security
      children:
        - tags: [password-cracking, encryption]
          name: Password attacks
        - tags: "#(cheatsheet|resources)"
        - learn
        - MISC:
          - draft
          - tags: todo
            name: TODO
    - programming:
      - python
      - tags: [typescript, javascript, js, ts]
        name: JavaScript
```
