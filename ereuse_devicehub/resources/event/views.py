from distutils.version import StrictVersion

from flask import request

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.sync import Sync
from ereuse_devicehub.resources.event.enums import SoftwareType
from ereuse_devicehub.resources.event.models import Event, Snapshot, TestHardDrive
from teal.resource import View


class EventView(View):
    def one(self, id: int):
        """Gets one event."""
        return Event.query.filter_by(id=id).one()


SUPPORTED_WORKBENCH = StrictVersion('11.0')


class SnapshotView(View):
    def post(self):
        """Creates a Snapshot."""
        s = request.get_json()
        # Note that if we set the device / components into the snapshot
        # model object, when we flush them to the db we will flush
        # snapshot, and we want to wait to flush snapshot at the end
        device = s.pop('device')
        components = s.pop('components') if s['software'] == SoftwareType.Workbench else None
        # noinspection PyArgumentList
        snapshot = Snapshot(**s)
        snapshot.device, snapshot.events = Sync.run(device, components, snapshot.force_creation)
        snapshot.components = snapshot.device.components
        db.session.add(snapshot)
        db.session.flush()  # Take to DB so we get db-generated values
        ret = self.schema.jsonify(snapshot)  # transform it back
        ret.status_code = 201
        return ret


class TestHardDriveView(View):
    def post(self):
        t = request.get_json()  # type: dict
        # noinspection PyArgumentList
        test = TestHardDrive(snapshot_id=t.pop('snapshot'), device_id=t.pop('device'), **t)
        return test


class StressTestView(View):
    def post(self):
        t = request.get_json()  # type: dict
