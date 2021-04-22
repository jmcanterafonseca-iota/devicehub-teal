""" This is the view for Snapshots """

import os
import json
import shutil
from datetime import datetime, timedelta
from distutils.version import StrictVersion
from uuid import UUID

from flask import current_app as app, request, g
from sqlalchemy.util import OrderedSet
from teal.marshmallow import ValidationError
from teal.resource import View
from teal.db import ResourceNotFound

from ereuse_devicehub.db import db
from ereuse_devicehub.query import things_response
from ereuse_devicehub.resources.action.models import (Action, RateComputer, Snapshot, VisualTest,
                                                      InitTransfer, Live, Allocate, Deallocate,
                                                      Trade, Confirm)
from ereuse_devicehub.resources.device.models import Device, Computer, DataStorage
from ereuse_devicehub.resources.action.rate.v1_0 import CannotRate
from ereuse_devicehub.resources.enums import SnapshotSoftware, Severity
from ereuse_devicehub.resources.user.exceptions import InsufficientPermission
from ereuse_devicehub.resources.user.models import User

SUPPORTED_WORKBENCH = StrictVersion('11.0')


def save_json(req_json, tmp_snapshots, user, live=False):
    """
    This function allow save a snapshot in json format un a TMP_SNAPSHOTS directory
    The file need to be saved with one name format with the stamptime and uuid joins
    """
    uuid = req_json.get('uuid', '')
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day
    hour = now.hour
    minutes = now.minute

    name_file = f"{year}-{month}-{day}-{hour}-{minutes}_{user}_{uuid}.json"
    path_dir_base = os.path.join(tmp_snapshots, user)
    if live:
        path_dir_base = tmp_snapshots
    path_errors = os.path.join(path_dir_base, 'errors')
    path_fixeds = os.path.join(path_dir_base, 'fixeds')
    path_name = os.path.join(path_errors, name_file)

    if not os.path.isdir(path_dir_base):
        os.system(f'mkdir -p {path_errors}')
        os.system(f'mkdir -p {path_fixeds}')

    with open(path_name, 'w') as snapshot_file:
        snapshot_file.write(json.dumps(req_json))

    return path_name


def move_json(tmp_snapshots, path_name, user, live=False):
    """
    This function move the json than it's correct
    """
    path_dir_base = os.path.join(tmp_snapshots, user)
    if live:
        path_dir_base = tmp_snapshots
    if os.path.isfile(path_name):
        shutil.copy(path_name, path_dir_base)
        os.remove(path_name)


class AllocateMix():
    model = None

    def post(self):
        """ Create one res_obj """
        res_json = request.get_json()
        res_obj = self.model(**res_json)
        db.session.add(res_obj)
        db.session().final_flush()
        ret = self.schema.jsonify(res_obj)
        ret.status_code = 201
        db.session.commit()
        return ret

    def find(self, args: dict):
        res_objs = self.model.query.filter_by(author=g.user) \
            .order_by(self.model.created.desc()) \
            .paginate(per_page=200)
        return things_response(
            self.schema.dump(res_objs.items, many=True, nested=0),
            res_objs.page, res_objs.per_page, res_objs.total,
            res_objs.prev_num, res_objs.next_num
        )


class AllocateView(AllocateMix, View):
    model = Allocate


class DeallocateView(AllocateMix, View):
    model = Deallocate


class LiveView(View):
    def post(self):
        """Posts an action."""
        res_json = request.get_json(validate=False)
        tmp_snapshots = app.config['TMP_LIVES']
        path_live = save_json(res_json, tmp_snapshots, '', live=True)
        res_json.pop('debug', None)
        res_json.pop('elapsed', None)
        res_json.pop('os', None)
        res_json_valid = self.schema.load(res_json)
        live = self.live(res_json_valid)
        db.session.add(live)
        db.session().final_flush()
        ret = self.schema.jsonify(live)
        ret.status_code = 201
        db.session.commit()
        move_json(tmp_snapshots, path_live, '', live=True)
        return ret

    def get_hdd_details(self, snapshot, device):
        """We get the liftime and serial_number of the disk"""
        usage_time_hdd = None
        serial_number = None
        components = [c for c in snapshot['components']]
        components.sort(key=lambda x: x.created)
        for hd in components:
            if not isinstance(hd, DataStorage):
                continue

            serial_number = hd.serial_number
            for act in hd.actions:
                if not act.type == "TestDataStorage":
                    continue
                usage_time_hdd = act.lifetime
                break

            if usage_time_hdd:
                break

        if not serial_number:
            """There aren't any disk"""
            raise ResourceNotFound("There aren't any disk in this device {}".format(device))
        return usage_time_hdd, serial_number

    def get_hid(self, snapshot):
        device = snapshot.get('device')  # type: Computer
        components = snapshot.get('components')
        if not device:
            return None
        if not components:
            return device.hid
        macs = [c.serial_number for c in components
                if c.type == 'NetworkAdapter' and c.serial_number is not None]
        macs.sort()
        mac = ''
        hid = device.hid
        if not hid:
            return hid
        if macs:
            mac = "-{mac}".format(mac=macs[0])
        hid += mac
        return hid

    def live(self, snapshot):
        """If the device.allocated == True, then this snapshot create an action live."""
        hid = self.get_hid(snapshot)
        if not hid or not Device.query.filter(
            Device.hid==hid).count():
            raise ValidationError('Device not exist.')

        device = Device.query.filter(
            Device.hid==hid, Device.allocated==True).one()
        # Is not necessary
        if not device:
            raise ValidationError('Device not exist.')
        if not device.allocated:
            raise ValidationError('Sorry this device is not allocated.')

        usage_time_hdd, serial_number = self.get_hdd_details(snapshot, device)

        data_live = {'usage_time_hdd': usage_time_hdd,
                     'serial_number': serial_number,
                     'snapshot_uuid': snapshot['uuid'],
                     'description': '',
                     'software': snapshot['software'],
                     'software_version': snapshot['version'],
                     'licence_version': snapshot['licence_version'],
                     'author_id': device.owner_id,
                     'agent_id': device.owner.individual.id,
                     'device': device}

        live = Live(**data_live)

        if not usage_time_hdd:
            warning = f"We don't found any TestDataStorage for disk sn: {serial_number}"
            live.severity = Severity.Warning
            live.description = warning
            return live

        live.sort_actions()
        diff_time = live.diff_time()
        if diff_time is None:
            warning = "Don't exist one previous live or snapshot as reference"
            live.description += warning
            live.severity = Severity.Warning
        elif diff_time < timedelta(0):
            warning = "The difference with the last live/snapshot is negative"
            live.description += warning
            live.severity = Severity.Warning
        return live


class ActionView(View):
    def post(self):
        """Posts an action."""
        json = request.get_json(validate=False)
        if not json or 'type' not in json:
            raise ValidationError('Resource needs a type.')
        # todo there should be a way to better get subclassess resource
        #   defs
        resource_def = app.resources[json['type']]
        if json['type'] == Snapshot.t:
            tmp_snapshots = app.config['TMP_SNAPSHOTS']
            path_snapshot = save_json(json, tmp_snapshots, g.user.email)
            json.pop('debug', None)
            a = resource_def.schema.load(json)
            response = self.snapshot(a, resource_def)
            move_json(tmp_snapshots, path_snapshot, g.user.email)
            return response
        if json['type'] == VisualTest.t:
            pass
            # TODO JN add compute rate with new visual test and old components device
        if json['type'] == InitTransfer.t:
            return self.transfer_ownership()
        # import pdb; pdb.set_trace()
        a = resource_def.schema.load(json)
        Model = db.Model._decl_class_registry.data[json['type']]()
        action = Model(**a)
        if json['type'] == Trade.t:
            return self.offer(action)
        db.session.add(action)
        db.session().final_flush()
        ret = self.schema.jsonify(action)
        ret.status_code = 201
        db.session.commit()
        return ret

    def one(self, id: UUID):
        """Gets one action."""
        action = Action.query.filter_by(id=id).one()
        return self.schema.jsonify(action)

    def snapshot(self, snapshot_json: dict, resource_def):
        """Performs a Snapshot.

        See `Snapshot` section in docs for more info.
        """
        # Note that if we set the device / components into the snapshot
        # model object, when we flush them to the db we will flush
        # snapshot, and we want to wait to flush snapshot at the end

        device = snapshot_json.pop('device')  # type: Computer
        components = None
        if snapshot_json['software'] == (SnapshotSoftware.Workbench or SnapshotSoftware.WorkbenchAndroid):
            components = snapshot_json.pop('components', None)  # type: List[Component]
            if isinstance(device, Computer) and device.hid:
                device.add_mac_to_hid(components_snap=components)
        snapshot = Snapshot(**snapshot_json)

        # Remove new actions from devices so they don't interfere with sync
        actions_device = set(e for e in device.actions_one)
        device.actions_one.clear()
        if components:
            actions_components = tuple(set(e for e in c.actions_one) for c in components)
            for component in components:
                component.actions_one.clear()

        assert not device.actions_one
        assert all(not c.actions_one for c in components) if components else True
        db_device, remove_actions = resource_def.sync.run(device, components)

        del device  # Do not use device anymore
        snapshot.device = db_device
        snapshot.actions |= remove_actions | actions_device  # Set actions to snapshot
        # commit will change the order of the components by what
        # the DB wants. Let's get a copy of the list so we preserve order
        ordered_components = OrderedSet(x for x in snapshot.components)

        # Add the new actions to the db-existing devices and components
        db_device.actions_one |= actions_device
        if components:
            for component, actions in zip(ordered_components, actions_components):
                component.actions_one |= actions
                snapshot.actions |= actions

        if snapshot.software == SnapshotSoftware.Workbench:
            # Check ownership of (non-component) device to from current.user
            if db_device.owner_id != g.user.id:
                raise InsufficientPermission()
            # Compute ratings
            try:
                rate_computer, price = RateComputer.compute(db_device)
            except CannotRate:
                pass
            else:
                snapshot.actions.add(rate_computer)
                if price:
                    snapshot.actions.add(price)
        elif snapshot.software == SnapshotSoftware.WorkbenchAndroid:
            pass  # TODO try except to compute RateMobile
        # Check if HID is null and add Severity:Warning to Snapshot
        if snapshot.device.hid is None:
            snapshot.severity = Severity.Warning

        db.session.add(snapshot)
        db.session().final_flush()
        ret = self.schema.jsonify(snapshot)  # transform it back
        ret.status_code = 201
        db.session.commit()
        return ret

    def transfer_ownership(self):
        """Perform a InitTransfer action to change author_id of device"""
        pass

    def offer(self, offer: Trade):
        self.create_first_confirmation(offer)
        self.create_phantom_account(offer)
        db.session.add(offer)
        self.create_automatic_trade(offer)

        db.session().final_flush()
        ret = self.schema.jsonify(offer)
        ret.status_code = 201
        db.session.commit()
        return ret

    def create_first_confirmation(self, offer: Trade) -> None:
        """Do the first confirmation for the user than do the action"""

        # check than the user than want to do the action is one of the users
        # involved in the action
        assert g.user.id in [offer.user_from_id, offer.user_to_id]

        confirm = Confirm(user=g.user, action=offer, devices=offer.devices)
        db.session.add(confirm)

    def create_phantom_account(self, offer) -> None:
        """
        If exist both users not to do nothing
        If exist from but not to:
            search if exist in the DB
                if exist use it
                else create new one
        The same if exist to but not from

        """
        if offer.user_from_id and offer.user_to_id:
            return

        if offer.user_from_id and not offer.user_to_id:
            assert g.user.id == offer.user_from_id
            email = "{}_{}@dhub.com".format(str(offer.user_from_id), offer.code)
            users = User.query.filter_by(email=email)
            if users.first():
                user = users.first()
                offer.user_to = user
                return

            user = User(email=email, password='', active=False, phantom=True)
            db.session.add(user)
            offer.user_to = user

        if not offer.user_from_id and offer.user_to_id:
            email = "{}_{}@dhub.com".format(str(offer.user_to_id), offer.code)
            users = User.query.filter_by(email=email)
            if users.first():
                user = users.first()
                offer.user_from = user
                return

            user = User(email=email, password='', active=False, phantom=True)
            db.session.add(user)
            offer.user_from = user

    def create_automatic_trade(self, offer: Trade) -> None:
        # not do nothing if it's neccesary confirmation explicity
        if offer.confirm:
            return

        # Change the owner for every devices
        for dev in offer.devices:
            dev.owner = offer.user_to
            if hasattr(dev, 'components'):
                for c in dev.components:
                    c.owner = offer.user_to

        # Create a new Confirmation for the user who does not perform the action
        user = offer.user_from
        if g.user == offer.user_from:
            user = offer.user_to
        confirm = Confirm(user=user, action=offer, devices=offer.devices)
        db.session.add(confirm)
