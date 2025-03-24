import os
from jira import JIRA


if __name__ == "__main__":
    print("This is the main function")
    jira = JIRA(
        server=os.getenv('JIRA_SERVER'),
        basic_auth=(os.getenv('JIRA_USER'), os.getenv('JIRA_PASS'))
    )

    user = jira.myself()

    project = jira.project(id='PAM2017')

    components = jira.project_components(project.id)

    versions = jira.project_versions(project.id)

    issue_types = jira.project_issue_types(project.id)
    project_issue_fields = {}
    for issue_type in issue_types:
        issue_fields = jira.project_issue_fields(project.id, issue_type.id)
        project_issue_fields[issue_type.name] = issue_fields

    print(project_issue_fields)
    print('END')



