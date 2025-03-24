import base64
import os

import requests
import yaml
from atlassian import Xray, Jira

from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime

from dacite import from_dict
from typing_extensions import override


@dataclass
class XRayTestStepAttachment:
    author: Optional[str] = None
    authorFullName: Optional[str] = None
    created: Optional[str] = None
    createdDate: Optional[int] = None
    fileIcon: Optional[str] = None
    fileIconAlt: Optional[str] = None
    fileName: Optional[str] = None
    filePath: Optional[str] = None
    fileSize: Optional[str] = None
    fileURL: Optional[str] = None
    id: Optional[int] = None
    mimeType: Optional[str] = None
    numericalFileSize: Optional[int] = None


@dataclass
class XRayTestStepData:
    raw: Optional[str] = None
    rendered: Optional[str] = None


@dataclass
class XRayTestStep:
    attachments: Optional[List[XRayTestStepAttachment]] = None
    data: Optional[XRayTestStepData] = None
    id: Optional[int] = None
    index: Optional[int] = None
    result: Optional[XRayTestStepData] = None
    step: Optional[XRayTestStepData] = None


def convert_file_to_base64(file_path):
    try:
        # Open the file in binary read mode
        with open(file_path, "rb") as file:
            # Read file content and encode it to base64
            base64_content = base64.b64encode(file.read()).decode('utf-8')
        return base64_content
    except Exception as e:
        print(f"Error reading or encoding the file: {e}")
        return None


class XRayPlus(Xray):

    def create_test_step_with_attachments(self, test_key, step, data, result, attachments):
        """
        Create a new test steps for a given test.
        NOTE: attachments are currently not supported!
        :param test_key: Test key (eg. 'TEST-001').
        :param step: Test Step name (eg. 'Example step').
        :param data: Test Step data (eg. 'Example data').
        :param result: Test Step results (eg. 'Example results').
        :param attachments: Test Step attachments (eg. 'Example attachments').
        :return:
        """
        create = {"step": step, "data": data, "result": result, "attachments": attachments}
        url = self.resource_url("test/{0}/step".format(test_key))
        return self.put(url, create)


def pull_test_steps(issue_key: str, xray: Xray) -> List[XRayTestStep]:
    steps = xray.get_test_steps(issue_key)
    return [from_dict(data_class=XRayTestStep, data=step) for step in steps]


@dataclass
class TestStepAttachment:
    filename: Optional[str] = None
    filepath: Optional[str] = None
    content_type: Optional[str] = None

@dataclass
class TestStep:
    name: Optional[str] = None
    step: Optional[str] = None
    data: Optional[str] = None
    result: Optional[str] = None
    attachments: Optional[List[TestStepAttachment]] = None

@dataclass
class Test:
    name: Optional[str] = None
    description: Optional[str] = None
    issue_key: Optional[str] = None
    steps: Optional[List[TestStep]] = None

@dataclass
class TestInfo:
    name: Optional[str] = None
    path: Optional[str] = None

@dataclass
class TestSet:
    name: Optional[str] = None
    issue_key: Optional[str] = None
    description: Optional[str] = None
    tests: Optional[List[TestInfo]] = None



if __name__ == "__main__":

    xray = XRayPlus(
        url=os.getenv('JIRA_SERVER'),
        username=os.getenv('JIRA_USER'),
        password=os.getenv('JIRA_PASS'))

    jira = Jira(
        url=os.getenv('JIRA_SERVER'),
        username=os.getenv('JIRA_USER'),
        password=os.getenv('JIRA_PASS'))

    jira_project = 'PAM2017'

    """
    Test Set
    """
    test_set_path =  r'D:\repo\TBOG\Tests\zulu'
    test_set_manifest = os.path.join(test_set_path, 'tests.yml')

    with open(test_set_manifest) as f:
        test_set_data = yaml.safe_load(f)

    test_set = from_dict(data_class=TestSet, data=test_set_data)

    # Check if the TestSet has an issue key and create it if it does not
    test_set_issue = None
    # Check if the TestSet has an issue key
    if test_set.issue_key and jira.issue_exists(test_set.issue_key):
        # Retrieve the issue
        test_set_issue = jira.issue(test_set.issue_key)

    # Create the issue if it does not exist
    if not test_set_issue:
        created_issue = jira.create_issue(
            {
                'project': {'key': jira_project},
                'summary': test_set.name,
                'description': test_set.description,
                'issuetype': {'name': 'Test Set'}
            })
        test_set.issue_key = created_issue['key']

    # Update Test Set Manifest
    with open(test_set_manifest, 'w') as f:
        yaml.dump(asdict(test_set), f)

    """
    Tests
    """

    for test in test_set.tests:
        test_path = os.path.join(test_set_path, test.path)
        test_manifest = os.path.join(test_path, 'test.yml')

        # Push test steps to a Jira issue
        with open(test_manifest) as f:
            test_data = yaml.safe_load(f)

        test = from_dict(data_class=Test, data=test_data)

        # Check if issue exists
        jira_issue = None
        if test.issue_key and jira.issue_exists(test.issue_key):
            jira_issue = jira.issue(test.issue_key)

        # If issue does not exist, create it
        if not jira_issue or not test.issue_key:
            created_issue = jira.create_issue({
                'project': {'key': jira_project},
                'summary': test.name,
                'description': test.description,
                'issuetype': {'name': 'Test Set'}
            })
            test.issue_key = created_issue['key']

        # Update Jira Issue Summary
        if jira_issue['fields']['summary'] != test.name:
            jira.update_issue_field(
                key=test.issue_key,
                fields={'summary': test.name})

        # Update Jira Issue Description
        if jira_issue['fields']['description'] != test.description:
            jira.update_issue_field(
                key=test.issue_key,
                fields={'description': test.description})

        # Clear existing test steps
        xray_test_steps = xray.get_test_steps(test.issue_key)
        for xray_test_step in xray_test_steps:
            xray.delete_test_step(test.issue_key, xray_test_step['id'])

        # Create new test steps
        test_steps = test.steps
        for test_step in test_steps:

            attachments = []
            for attachment in test_step.attachments:
                attachments.append({
                    "data": convert_file_to_base64(attachment.filepath),
                    "filename": attachment.filename,
                    "contentType": attachment.content_type
                })

            xray.create_test_step_with_attachments(
                test_key=test.issue_key,
                step=test_step.step,
                data=test_step.data,
                result=test_step.result,
                attachments=attachments)

        # Update Test Manifest
        with open(test_manifest, 'w') as f:
            yaml.dump(asdict(test), f)