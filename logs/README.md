# Logs Directory

This folder stores runtime logs created by `start_all.sh`.

⚠️ Note: The contents of this directory are excluded from version control
via `.gitignore`. Only this README file is tracked to keep the folder present.

## Log Files

- `eliza.log`: Eliza ingest service logs
- `pumpfun.log`: Pumpfun bot runtime logs

## Usage

These logs are automatically created when running `start_all.sh`. You can view them using:

```bash
tail -f logs/eliza.log logs/pumpfun.log
```