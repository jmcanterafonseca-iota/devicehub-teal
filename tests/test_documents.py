import csv
from datetime import datetime
from io import StringIO
from pathlib import Path

import pytest
import teal.marshmallow
from ereuse_utils.test import ANY

from ereuse_devicehub.client import Client, UserClient
from ereuse_devicehub.resources.action.models import Snapshot
from ereuse_devicehub.resources.documents import documents
from tests.conftest import file


@pytest.mark.mvp
def test_erasure_certificate_public_one(user: UserClient, client: Client):
    """Public user can get certificate from one device as HTML or PDF."""
    s = file('erase-sectors.snapshot')
    snapshot, _ = user.post(s, res=Snapshot)

    doc, response = client.get(res=documents.DocumentDef.t,
                               item='erasures/{}'.format(snapshot['device']['id']),
                               accept=ANY)
    assert 'html' in response.content_type
    assert '<html' in doc
    assert '2018' in doc

    doc, response = client.get(res=documents.DocumentDef.t,
                               item='erasures/{}'.format(snapshot['device']['id']),
                               query=[('format', 'PDF')],
                               accept='application/pdf')
    assert 'application/pdf' == response.content_type

    erasure = next(e for e in snapshot['actions'] if e['type'] == 'EraseSectors')

    doc, response = client.get(res=documents.DocumentDef.t,
                               item='erasures/{}'.format(erasure['id']),
                               accept=ANY)
    assert 'html' in response.content_type
    assert '<html' in doc
    assert '2018' in doc


@pytest.mark.mvp
def test_erasure_certificate_private_query(user: UserClient):
    """Logged-in user can get certificates using queries as HTML and
    PDF.
    """
    s = file('erase-sectors.snapshot')
    snapshot, response = user.post(s, res=Snapshot)

    doc, response = user.get(res=documents.DocumentDef.t,
                             item='erasures/',
                             query=[('filter', {'id': [snapshot['device']['id']]})],
                             accept=ANY)
    assert 'html' in response.content_type
    assert '<html' in doc
    assert '2018' in doc

    doc, response = user.get(res=documents.DocumentDef.t,
                             item='erasures/',
                             query=[
                                 ('filter', {'id': [snapshot['device']['id']]}),
                                 ('format', 'PDF')
                             ],
                             accept='application/pdf')
    assert 'application/pdf' == response.content_type


@pytest.mark.mvp
def test_erasure_certificate_wrong_id(client: Client):
    client.get(res=documents.DocumentDef.t, item='erasures/this-is-not-an-id',
               status=teal.marshmallow.ValidationError)


@pytest.mark.mvp
def test_export_basic_snapshot(user: UserClient):
    """Test export device information in a csv file."""
    snapshot, _ = user.post(file('basic.snapshot'), res=Snapshot)
    csv_str, _ = user.get(res=documents.DocumentDef.t,
                          item='devices/',
                          accept='text/csv',
                          query=[('filter', {'type': ['Computer']})])
    f = StringIO(csv_str)
    obj_csv = csv.reader(f, f)
    export_csv = list(obj_csv)

    # Open fixture csv and transform to list
    with Path(__file__).parent.joinpath('files').joinpath('basic.csv').open() as csv_file:
        obj_csv = csv.reader(csv_file)
        fixture_csv = list(obj_csv)

    assert isinstance(datetime.strptime(export_csv[1][8], '%c'), datetime), \
        'Register in field is not a datetime'

    # Pop dates fields from csv lists to compare them
    fixture_csv[1] = fixture_csv[1][:8] + fixture_csv[1][9:]
    export_csv[1] = export_csv[1][:8] + export_csv[1][9:]

    assert fixture_csv[0] == export_csv[0], 'Headers are not equal'
    assert fixture_csv[1] == export_csv[1], 'Computer information are not equal'


@pytest.mark.mvp
def test_export_full_snapshot(user: UserClient):
    """Test a export device with all information and a lot of components."""
    snapshot, _ = user.post(file('real-eee-1001pxd.snapshot.11'), res=Snapshot)
    csv_str, _ = user.get(res=documents.DocumentDef.t,
                          item='devices/',
                          accept='text/csv',
                          query=[('filter', {'type': ['Computer']})])
    f = StringIO(csv_str)
    obj_csv = csv.reader(f, f)
    export_csv = list(obj_csv)

    # Open fixture csv and transform to list
    with Path(__file__).parent.joinpath('files').joinpath('real-eee-1001pxd.csv').open() \
            as csv_file:
        obj_csv = csv.reader(csv_file)
        fixture_csv = list(obj_csv)

    assert isinstance(datetime.strptime(export_csv[1][8], '%c'), datetime), \
        'Register in field is not a datetime'

    # Pop dates fields from csv lists to compare them
    fixture_csv[1] = fixture_csv[1][:8] + fixture_csv[1][9:]
    export_csv[1] = export_csv[1][:8] + export_csv[1][9:]

    assert fixture_csv[0] == export_csv[0], 'Headers are not equal'
    assert fixture_csv[1] == export_csv[1], 'Computer information are not equal'


@pytest.mark.mvp
def test_export_empty(user: UserClient):
    """Test to check works correctly exporting csv without any information,
    export a placeholder device.
    """
    csv_str, _ = user.get(res=documents.DocumentDef.t,
                          accept='text/csv',
                          item='devices/')
    f = StringIO(csv_str)
    obj_csv = csv.reader(f, f)
    export_csv = list(obj_csv)

    assert len(export_csv) == 0, 'Csv is not empty'


@pytest.mark.mvp
def test_export_computer_monitor(user: UserClient):
    """Test a export device type computer monitor."""
    snapshot, _ = user.post(file('computer-monitor.snapshot'), res=Snapshot)
    csv_str, _ = user.get(res=documents.DocumentDef.t,
                          item='devices/',
                          accept='text/csv',
                          query=[('filter', {'type': ['ComputerMonitor']})])
    f = StringIO(csv_str)
    obj_csv = csv.reader(f, f)
    export_csv = list(obj_csv)
    # Open fixture csv and transform to list
    with Path(__file__).parent.joinpath('files').joinpath('computer-monitor.csv').open() \
            as csv_file:
        obj_csv = csv.reader(csv_file)
        fixture_csv = list(obj_csv)

    # Pop dates fields from csv lists to compare them
    fixture_csv[1] = fixture_csv[1][:8]
    export_csv[1] = export_csv[1][:8]

    assert fixture_csv[0] == export_csv[0], 'Headers are not equal'
    assert fixture_csv[1] == export_csv[1], 'Component information are not equal'


def test_export_keyboard(user: UserClient):
    """Test a export device type keyboard."""
    snapshot, _ = user.post(file('keyboard.snapshot'), res=Snapshot)
    csv_str, _ = user.get(res=documents.DocumentDef.t,
                          item='devices/',
                          accept='text/csv',
                          query=[('filter', {'type': ['Keyboard']})])
    f = StringIO(csv_str)
    obj_csv = csv.reader(f, f)
    export_csv = list(obj_csv)
    # Open fixture csv and transform to list
    with Path(__file__).parent.joinpath('files').joinpath('keyboard.csv').open() as csv_file:
        obj_csv = csv.reader(csv_file)
        fixture_csv = list(obj_csv)

    # Pop dates fields from csv lists to compare them
    fixture_csv[1] = fixture_csv[1][:8]
    export_csv[1] = export_csv[1][:8]

    assert fixture_csv[0] == export_csv[0], 'Headers are not equal'
    assert fixture_csv[1] == export_csv[1], 'Component information are not equal'


@pytest.mark.mvp
def test_export_multiple_different_devices(user: UserClient):
    """Test function 'Export' of multiple different device types (like
    computers, keyboards, monitors, etc..)
    """
    # Open fixture csv and transform to list
    with Path(__file__).parent.joinpath('files').joinpath('multiples_devices.csv').open() \
            as csv_file:
        fixture_csv = list(csv.reader(csv_file))
    for row in fixture_csv:
        del row[8]  # We remove the 'Registered in' column

    # Post all devices snapshots
    snapshot_pc, _ = user.post(file('real-eee-1001pxd.snapshot.11'), res=Snapshot)
    snapshot_empty, _ = user.post(file('basic.snapshot'), res=Snapshot)
    snapshot_keyboard, _ = user.post(file('keyboard.snapshot'), res=Snapshot)
    snapshot_monitor, _ = user.post(file('computer-monitor.snapshot'), res=Snapshot)

    csv_str, _ = user.get(res=documents.DocumentDef.t,
                          item='devices/',
                          query=[('filter', {'type': ['Computer', 'Keyboard', 'Monitor']})],
                          accept='text/csv')
    f = StringIO(csv_str)
    obj_csv = csv.reader(f, f)
    export_csv = list(obj_csv)

    for row in export_csv:
        del row[8]

    assert fixture_csv == export_csv


@pytest.mark.mvp
def test_report_devices_stock_control(user: UserClient, user2: UserClient):
    """Test export device information in a csv file."""
    snapshot, _ = user.post(file('basic.snapshot'), res=Snapshot)
    snapshot2, _ = user2.post(file('basic.snapshot2'), res=Snapshot)

    csv_str, _ = user.get(res=documents.DocumentDef.t,
                          item='stock/',
                          accept='text/csv',
                          query=[('filter', {'type': ['Computer']})])
    f = StringIO(csv_str)
    obj_csv = csv.reader(f, f)
    export_csv = list(obj_csv)

    # Open fixture csv and transform to list
    with Path(__file__).parent.joinpath('files').joinpath('basic-stock.csv').open() as csv_file:
        obj_csv = csv.reader(csv_file)
        fixture_csv = list(obj_csv)

    assert user.user['id'] != user2.user['id']
    assert len(export_csv) == 2

    assert isinstance(datetime.strptime(export_csv[1][5], '%c'), datetime), \
        'Register in field is not a datetime'

    # Pop dates fields from csv lists to compare them
    fixture_csv[1] = fixture_csv[1][:5] + fixture_csv[1][6:]
    export_csv[1] = export_csv[1][:5] + export_csv[1][6:]

    assert fixture_csv[0] == export_csv[0], 'Headers are not equal'
    assert fixture_csv[1] == export_csv[1], 'Computer information are not equal'
