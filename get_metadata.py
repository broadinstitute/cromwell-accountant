import firecloud.api as fapi
import sys

if __name__ == "__main__":
   
    #get_workflow_metadata(namespace, workspace, submission_id, workflow_id)
    namespace = "clara-terra"
    workspace="Clara-Parabricks"
    submission_id = sys.argv[1]
    workflow_id = sys.argv[2]
    resp = fapi.get_workflow_metadata(namespace, workspace, submission_id, workflow_id)
    with open("metadata.json", "w") as ofi:
        ofi.write(resp.text)
