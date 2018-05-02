This script estimates the cost of running a Cromwell pipeline
based on Cromwell metadata JSON, which is a full response to
`GET https://${chromwell_host}/api/workflows/v1/{workflow_id}/metadata`.

You can use it in the following format:
```bash
./cost.py < metadata.json
```

It fetches the current [GCP price list](http://cloudpricingcalculator.appspot.com/static/data/pricelist.json)
and calculates the cost of each task call
based on the hourly price of its machine type and disk type and size.
Then, it sums up the costs of all calls and prints it to stdout.

**Note:** This script can be used on the workflows that are still running.
