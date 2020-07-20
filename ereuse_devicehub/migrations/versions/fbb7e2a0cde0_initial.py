"""Initial

Revision ID: fbb7e2a0cde0
Revises:
Create Date: 2020-05-07 10:04:40.269511

"""
import os
from alembic import op
from alembic import context
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlalchemy_utils
import citext

import teal
from ereuse_devicehub.resources.enums import TransferState, Severity

# revision identifiers, used by Alembic.
revision = 'fbb7e2a0cde0'
down_revision = None
branch_labels = None
depends_on = None

def get_inv():
    INV = context.get_x_argument(as_dictionary=True).get('inventory')
    if not INV:
        raise ValueError("Inventory value is not specified")
    return INV


def upgrade():
    # Create Common schema
    op.execute("create schema common")
    op.execute(f"create schema {get_inv()}")

    # Inventory table
    op.create_table('inventory',
                    sa.Column('updated', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='The last time Devicehub recorded a change for \n    this thing.\n    '),
                    sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='When Devicehub created this.'),
                    sa.Column('id', sa.Unicode(), nullable=False, comment='The name of the inventory as in the URL and schema.'),
                    sa.Column('name', citext.CIText(), nullable=False, comment='The human name of the inventory.'),
                    sa.Column('tag_provider', teal.db.URL(), nullable=False),
                    sa.Column('tag_token', postgresql.UUID(as_uuid=True), nullable=False, comment='The token to access a Tag service.'),
                    sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('name'),
                    sa.UniqueConstraint('tag_token'),
                    schema='common'
                    )
    op.create_index('id_hash', 'inventory', ['id'], unique=False, schema='common', postgresql_using='hash')
    op.create_index(op.f('ix_common_inventory_created'), 'inventory', ['created'], unique=False, schema='common')
    op.create_index(op.f('ix_common_inventory_updated'), 'inventory', ['updated'], unique=False, schema='common')

    # Manufacturer table
    op.create_table('manufacturer',
                    sa.Column('name', citext.CIText(), nullable=False, comment='The normalized name of the manufacturer.'),
                    sa.Column('url', teal.db.URL(), nullable=True, comment='An URL to a page describing the manufacturer.'),
                    sa.Column('logo', teal.db.URL(), nullable=True, comment='An URL pointing to the logo of the manufacturer.'),
                    sa.PrimaryKeyConstraint('name'),
                    sa.UniqueConstraint('url'),
                    schema='common'
                    )

    # User table
    op.create_table('user',
                    sa.Column('updated', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='The last time Devicehub recorded a change for \n    this thing.\n    '),
                    sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='When Devicehub created this.'),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('email', sqlalchemy_utils.types.email.EmailType(length=255), nullable=False),
                    sa.Column('password', sqlalchemy_utils.types.password.PasswordType(max_length=64), nullable=True),
                    sa.Column('token', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('ethereum_address', citext.CIText(), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('email'),
                    sa.UniqueConstraint('ethereum_address'),
                    sa.UniqueConstraint('token'),
                    schema='common'
                    )
    op.create_index(op.f('ix_common_user_created'), 'user', ['created'], unique=False, schema='common')
    op.create_index(op.f('ix_common_user_updated'), 'user', ['updated'], unique=False, schema='common')

    # User Inventory table
    op.create_table('user_inventory',
                    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('inventory_id', sa.Unicode(), nullable=False),
                    sa.ForeignKeyConstraint(['inventory_id'], ['common.inventory.id'], ),
                    sa.ForeignKeyConstraint(['user_id'], ['common.user.id'], ),
                    sa.PrimaryKeyConstraint('user_id', 'inventory_id'),
                    schema='common'
                    )

    # Device table
    op.create_table('device',
                    sa.Column('updated', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='The last time Devicehub recorded a change for \n    this thing.\n    '),
                    sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='When Devicehub created this.'),
                    sa.Column('id', sa.BigInteger(), nullable=False, comment='The identifier of the device for this database. Used only\n    internally for software; users should not use this.\n    '),
                    sa.Column('type', sa.Unicode(length=32), nullable=False),
                    sa.Column('hid', sa.Unicode(), nullable=True, comment='The Hardware ID (HID) is the unique ID traceability\n    systems use to ID a device globally. This field is auto-generated\n    from Devicehub using literal identifiers from the device,\n    so it can re-generated *offline*.\n    \n        The HID is the result of concatenating,\n        in the following order: the type of device (ex. Computer),\n        the manufacturer name, the model name, and the S/N. It is joined\n        with hyphens, and adapted to comply with the URI specification, so\n        it can be used in the URI identifying the device on the Internet.\n        The conversion is done as follows:\n    \n        1. non-ASCII characters are converted to their ASCII equivalent or\n           removed.\n        2. Characterst that are not letters or numbers are converted to \n           underscores, in a way that there are no trailing underscores\n           and no underscores together, and they are set to lowercase.\n        \n        Ex. ``laptop-acer-aod270-lusga_0d0242201212c7614``\n    '),
                    sa.Column('model', sa.Unicode(), nullable=True, comment='The model of the device in lower case.\n\n\n    The model is the unambiguous, as technical as possible, denomination\n    for the product. This field, among others, is used to identify\n    the product.\n    '),
                    sa.Column('manufacturer', sa.Unicode(), nullable=True, comment='The normalized name of the manufacturer,\n    in lower case.\n\n    Although as of now Devicehub does not enforce normalization,\n    users can choose a list of normalized manufacturer names\n    from the own ``/manufacturers`` REST endpoint.\n    '),
                    sa.Column('serial_number', sa.Unicode(), nullable=True, comment='The serial number of the device in lower case.'),
                    sa.Column('brand', citext.CIText(), nullable=True, comment='A naming for consumers. This field can represent\n    several models, so it can be ambiguous, and it is not used to\n    identify the product.\n    '),
                    sa.Column('generation', sa.SmallInteger(), nullable=True, comment='The generation of the device.'),
                    sa.Column('version', citext.CIText(), nullable=True, comment='The version code of this device, like v1 or A001.'),
                    sa.Column('weight', sa.Float(decimal_return_scale=4), nullable=True, comment='The weight of the device in Kg.'),
                    sa.Column('width', sa.Float(decimal_return_scale=4), nullable=True, comment='The width of the device in meters.'),
                    sa.Column('height', sa.Float(decimal_return_scale=4), nullable=True, comment='The height of the device in meters.'),
                    sa.Column('depth', sa.Float(decimal_return_scale=4), nullable=True, comment='The depth of the device in meters.'),
                    sa.Column('color', sqlalchemy_utils.types.color.ColorType(length=20), nullable=True, comment='The predominant color of the device.'),
                    sa.Column('production_date', sa.DateTime(), nullable=True, comment='The date of production of the device.\n    This is timezone naive, as Workbench cannot report this data with timezone information.\n    '),
                    sa.Column('variant', citext.CIText(), nullable=True, comment='A variant or sub-model of the device.'),
                    sa.Column('sku', citext.CIText(), nullable=True, comment='The Stock Keeping Unit (SKU), i.e. a\n    merchant-specific identifier for a product or service.\n    '),
                    sa.Column('image', teal.db.URL(), nullable=True, comment='An image of the device.'),
                    sa.Column('max_drill_bit_size', sa.SmallInteger(), nullable=True),
                    sa.Column('size', sa.SmallInteger(), nullable=True, comment='The capacity in Liters.'),
                    sa.Column('max_allowed_weight', sa.Integer(), nullable=True),
                    sa.Column('wheel_size', sa.SmallInteger(), nullable=True),
                    sa.Column('gears', sa.SmallInteger(), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )
    op.create_index('device_id', 'device', ['id'], unique=False, postgresql_using='hash', schema=f'{get_inv()}')
    op.create_index(op.f('ix_device_created'), 'device', ['created'], unique=False, schema=f'{get_inv()}')
    op.create_index(op.f('ix_device_updated'), 'device', ['updated'], unique=False, schema=f'{get_inv()}')
    op.create_index('type_index', 'device', ['type'], unique=False, postgresql_using='hash', schema=f'{get_inv()}')
    op.create_table('agent',
                    sa.Column('updated', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='The last time Devicehub recorded a change for \n    this thing.\n    '),
                    sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='When Devicehub created this.'),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('type', sa.Unicode(), nullable=False),
                    sa.Column('name', citext.CIText(), nullable=True, comment='The name of the organization or person.'),
                    sa.Column('tax_id', sa.Unicode(length=32), nullable=True, comment='The Tax / Fiscal ID of the organization, \n    e.g. the TIN in the US or the CIF/NIF in Spain.\n    '),
                    sa.Column('country', sa.Enum('AF', 'AX', 'AL', 'DZ', 'AS', 'AD', 'AO', 'AI', 'AQ', 'AG', 'AR', 'AM', 'AW', 'AU', 'AT', 'AZ', 'BS', 'BH', 'BD', 'BB', 'BY', 'BE', 'BZ', 'BJ', 'BM', 'BT', 'BO', 'BQ', 'BA', 'BW', 'BV', 'BR', 'IO', 'BN', 'BG', 'BF', 'BI', 'KH', 'CM', 'CA', 'CV', 'KY', 'CF', 'TD', 'CL', 'CN', 'CX', 'CC', 'CO', 'KM', 'CG', 'CD', 'CK', 'CR', 'CI', 'HR', 'CU', 'CW', 'CY', 'CZ', 'DK', 'DJ', 'DM', 'DO', 'EC', 'EG', 'SV', 'GQ', 'ER', 'EE', 'ET', 'FK', 'FO', 'FJ', 'FI', 'FR', 'GF', 'PF', 'TF', 'GA', 'GM', 'GE', 'DE', 'GH', 'GI', 'GR', 'GL', 'GD', 'GP', 'GU', 'GT', 'GG', 'GN', 'GW', 'GY', 'HT', 'HM', 'VA', 'HN', 'HK', 'HU', 'IS', 'IN', 'ID', 'IR', 'IQ', 'IE', 'IM', 'IL', 'IT', 'JM', 'JP', 'JE', 'JO', 'KZ', 'KE', 'KI', 'KP', 'KR', 'KW', 'KG', 'LA', 'LV', 'LB', 'LS', 'LR', 'LY', 'LI', 'LT', 'LU', 'MO', 'MK', 'MG', 'MW', 'MY', 'MV', 'ML', 'MT', 'MH', 'MQ', 'MR', 'MU', 'YT', 'MX', 'FM', 'MD', 'MC', 'MN', 'ME', 'MS', 'MA', 'MZ', 'MM', 'NA', 'NR', 'NP', 'NL', 'NC', 'NZ', 'NI', 'NE', 'NG', 'NU', 'NF', 'MP', 'NO', 'OM', 'PK', 'PW', 'PS', 'PA', 'PG', 'PY', 'PE', 'PH', 'PN', 'PL', 'PT', 'PR', 'QA', 'RE', 'RO', 'RU', 'RW', 'BL', 'SH', 'KN', 'LC', 'MF', 'PM', 'VC', 'WS', 'SM', 'ST', 'SA', 'SN', 'RS', 'SC', 'SL', 'SG', 'SX', 'SK', 'SI', 'SB', 'SO', 'ZA', 'GS', 'SS', 'ES', 'LK', 'SD', 'SR', 'SJ', 'SZ', 'SE', 'CH', 'SY', 'TW', 'TJ', 'TZ', 'TH', 'TL', 'TG', 'TK', 'TO', 'TT', 'TN', 'TR', 'TM', 'TC', 'TV', 'UG', 'UA', 'AE', 'GB', 'US', 'UM', 'UY', 'UZ', 'VU', 'VE', 'VN', 'VG', 'VI', 'WF', 'EH', 'YE', 'ZM', 'ZW', name='country'), nullable=True, comment='Country issuing the tax_id number.'),
                    sa.Column('telephone', sqlalchemy_utils.types.phone_number.PhoneNumberType(length=20), nullable=True),
                    sa.Column('email', sqlalchemy_utils.types.email.EmailType(length=255), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('email'),
                    sa.UniqueConstraint('tax_id', 'country', name='Registration Number per country.'),
                    sa.UniqueConstraint('tax_id', 'name', name='One tax ID with one name.'),
                    schema=f'{get_inv()}'
                    )
    op.create_index('agent_type', 'agent', ['type'], unique=False, postgresql_using='hash', schema=f'{get_inv()}')
    op.create_index(op.f('ix_agent_created'), 'agent', ['created'], unique=False, schema=f'{get_inv()}')
    op.create_index(op.f('ix_agent_updated'), 'agent', ['updated'], unique=False, schema=f'{get_inv()}')

    # Computer table
    op.create_table('computer',
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.Column('chassis', sa.Enum('Tower', 'Docking', 'AllInOne', 'Microtower', 'PizzaBox', 'Lunchbox', 'Stick', 'Netbook', 'Handheld', 'Laptop', 'Convertible', 'Detachable', 'Tablet', 'Virtual', name='computerchassis'), nullable=False, comment='The physical form of the computer.\n\n    It is a subset of the Linux definition of DMI / DMI decode.\n    '),
                    sa.Column('ethereum_address', citext.CIText(), nullable=True),
                    sa.Column('deposit', sa.Integer(), nullable=True),
                    sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('transfer_state', teal.db.IntEnum(TransferState), nullable=False, comment='State of transfer for a given Lot of devices.\n    '),
                    sa.Column('receiver_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('deliverynote_address', citext.CIText(), nullable=True),
                    sa.Column('layout', sa.Enum('US', 'AF', 'ARA', 'AL', 'AM', 'AT', 'AU', 'AZ', 'BY', 'BE', 'BD', 'BA', 'BR', 'BG', 'DZ', 'MA', 'CM', 'MM', 'CA', 'CD', 'CN', 'HR', 'CZ', 'DK', 'NL', 'BT', 'EE', 'IR', 'IQ', 'FO', 'FI', 'FR', 'GH', 'GN', 'GE', 'DE', 'GR', 'HU', 'IL', 'IT', 'JP', 'KG', 'KH', 'KZ', 'LA', 'LATAM', 'LT', 'LV', 'MAO', 'ME', 'MK', 'MT', 'MN', 'NO', 'PL', 'PT', 'RO', 'RU', 'RS', 'SI', 'SK', 'ES', 'SE', 'CH', 'SY', 'TJ', 'LK', 'TH', 'TR', 'TW', 'UA', 'GB', 'UZ', 'VN', 'KR', 'IE', 'PK', 'MV', 'ZA', 'EPO', 'NP', 'NG', 'ET', 'SN', 'BRAI', 'TM', 'ML', 'TZ', 'TG', 'KE', 'BW', 'PH', 'MD', 'ID', 'MY', 'BN', 'IN', 'IS', 'NEC_VNDR_JP', name='layouts'), nullable=True, comment='Layout of a built-in keyboard of the computer,\n     if any.\n     '),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.device.id'], ),
                    sa.ForeignKeyConstraint(['owner_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['receiver_id'], ['common.user.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('ethereum_address'),
                    schema=f'{get_inv()}'
                    )

    # Computer accessory
    op.create_table('computer_accessory',
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.Column('layout', sa.Enum('US', 'AF', 'ARA', 'AL', 'AM', 'AT', 'AU', 'AZ', 'BY', 'BE', 'BD', 'BA', 'BR', 'BG', 'DZ', 'MA', 'CM', 'MM', 'CA', 'CD', 'CN', 'HR', 'CZ', 'DK', 'NL', 'BT', 'EE', 'IR', 'IQ', 'FO', 'FI', 'FR', 'GH', 'GN', 'GE', 'DE', 'GR', 'HU', 'IL', 'IT', 'JP', 'KG', 'KH', 'KZ', 'LA', 'LATAM', 'LT', 'LV', 'MAO', 'ME', 'MK', 'MT', 'MN', 'NO', 'PL', 'PT', 'RO', 'RU', 'RS', 'SI', 'SK', 'ES', 'SE', 'CH', 'SY', 'TJ', 'LK', 'TH', 'TR', 'TW', 'UA', 'GB', 'UZ', 'VN', 'KR', 'IE', 'PK', 'MV', 'ZA', 'EPO', 'NP', 'NG', 'ET', 'SN', 'BRAI', 'TM', 'ML', 'TZ', 'TG', 'KE', 'BW', 'PH', 'MD', 'ID', 'MY', 'BN', 'IN', 'IS', 'NEC_VNDR_JP', name='layouts'), nullable=True),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.device.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Device search table
    op.create_table('device_search',
                    sa.Column('device_id', sa.BigInteger(), nullable=False),
                    sa.Column('properties', postgresql.TSVECTOR(), nullable=False),
                    sa.Column('tags', postgresql.TSVECTOR(), nullable=True),
                    sa.ForeignKeyConstraint(['device_id'], [f'{get_inv()}.device.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('device_id'),
                    schema=f'{get_inv()}'
                    )
    op.create_index('properties gist', 'device_search', ['properties'], unique=False, postgresql_using='gist', schema=f'{get_inv()}')
    op.create_index('tags gist', 'device_search', ['tags'], unique=False, postgresql_using='gist', schema=f'{get_inv()}')

    # Lot table
    op.create_table('lot',
                    sa.Column('updated', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='The last time Devicehub recorded a change for \n    this thing.\n    '),
                    sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='When Devicehub created this.'),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('name', citext.CIText(), nullable=False),
                    sa.Column('description', citext.CIText(), nullable=True, comment='A comment about the lot.'),
                    sa.Column('closed', sa.Boolean(), nullable=False, comment='A closed lot cannot be modified anymore.'),
                    sa.Column('deposit', sa.Integer(), nullable=True),
                    sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('transfer_state', teal.db.IntEnum(TransferState), nullable=False, comment='State of transfer for a given Lot of devices.\n    '),
                    sa.Column('receiver_address', citext.CIText(), nullable=True),
                    sa.Column('deliverynote_address', citext.CIText(), nullable=True),
                    sa.ForeignKeyConstraint(['owner_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['receiver_address'], ['common.user.ethereum_address'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )
    op.create_index(op.f('ix_lot_created'), 'lot', ['created'], unique=False, schema=f'{get_inv()}')
    op.create_index(op.f('ix_lot_updated'), 'lot', ['updated'], unique=False, schema=f'{get_inv()}')

    # Mobile table
    op.create_table('mobile',
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.Column('imei', sa.BigInteger(), nullable=True, comment='The International Mobile Equipment Identity of\n    the smartphone as an integer.\n    '),
                    sa.Column('meid', sa.Unicode(), nullable=True, comment='The Mobile Equipment Identifier as a hexadecimal\n    string.\n    '),
                    sa.Column('ram_size', sa.Integer(), nullable=True, comment='The total of RAM of the device in MB.'),
                    sa.Column('data_storage_size', sa.Integer(), nullable=True, comment='The total of data storage of the device in MB'),
                    sa.Column('display_size', sa.Float(decimal_return_scale=1), nullable=True, comment='The total size of the device screen'),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.device.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Monitor table
    op.create_table('monitor',
                    sa.Column('size', sa.Float(decimal_return_scale=1), nullable=False, comment='The size of the monitor in inches.'),
                    sa.Column('technology', sa.Enum('CRT', 'TFT', 'LED', 'PDP', 'LCD', 'OLED', 'AMOLED', name='displaytech'), nullable=True, comment='The technology the monitor uses to display\n    the image.\n    '),
                    sa.Column('resolution_width', sa.SmallInteger(), nullable=False, comment='The maximum horizontal resolution the\n    monitor can natively support in pixels.\n    '),
                    sa.Column('resolution_height', sa.SmallInteger(), nullable=False, comment='The maximum vertical resolution the\n    monitor can natively support in pixels.\n    '),
                    sa.Column('refresh_rate', sa.SmallInteger(), nullable=True),
                    sa.Column('contrast_ratio', sa.SmallInteger(), nullable=True),
                    sa.Column('touchable', sa.Boolean(), nullable=True, comment='Whether it is a touchscreen.'),
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.device.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Networtking table
    op.create_table('networking',
                    sa.Column('speed', sa.SmallInteger(), nullable=True, comment='The maximum speed this network adapter can handle,\n    in mbps.\n    '),
                    sa.Column('wireless', sa.Boolean(), nullable=False, comment='Whether it is a wireless interface.'),
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.device.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Organization table
    op.create_table('organization',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.agent.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Printer table
    op.create_table('printer',
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.Column('wireless', sa.Boolean(), nullable=False, comment='Whether it is a wireless printer.'),
                    sa.Column('scanning', sa.Boolean(), nullable=False, comment='Whether the printer has scanning capabilities.'),
                    sa.Column('technology', sa.Enum('Toner', 'Inkjet', 'SolidInk', 'Dye', 'Thermal', name='printertechnology'), nullable=True, comment='Technology used to print.'),
                    sa.Column('monochrome', sa.Boolean(), nullable=False, comment='Whether the printer is only monochrome.'),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.device.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Proof table
    op.create_table('proof',
                    sa.Column('updated', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='The last time Devicehub recorded a change for \n    this thing.\n    '),
                    sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='When Devicehub created this.'),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('type', sa.Unicode(), nullable=False),
                    sa.Column('ethereum_hash', citext.CIText(), nullable=False),
                    sa.Column('device_id', sa.BigInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['device_id'], [f'{get_inv()}.device.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )
    op.create_index(op.f('ix_proof_created'), 'proof', ['created'], unique=False, schema=f'{get_inv()}')
    op.create_index(op.f('ix_proof_updated'), 'proof', ['updated'], unique=False, schema=f'{get_inv()}')

    # Action table
    op.create_table('action',
                    sa.Column('updated', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='The last time Devicehub recorded a change for \n    this thing.\n    '),
                    sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='When Devicehub created this.'),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('type', sa.Unicode(), nullable=False),
                    sa.Column('name', citext.CIText(), nullable=False, comment='A name or title for the action. Used when searching\n    for actions.\n    '),
                    sa.Column('severity', teal.db.IntEnum(Severity), nullable=False, comment='A flag evaluating the action execution. Ex. failed actions\n    have the value `Severity.Error`. Devicehub uses 4 severity levels:\n\n    * Info (Pass): default neutral severity. The action succeeded.\n    * Notice: The action succeeded but it is raising awareness.\n      Notices are not usually that important but something\n      (good or bad) worth checking.\n    * Warning: The action succeeded but there is something important\n      to check negatively affecting the action.\n    * Error (Fail): the action failed.\n\n    Devicehub specially raises user awareness when an action\n    has a Severity of ``Warning`` or greater.\n    '),
                    sa.Column('closed', sa.Boolean(), nullable=False, comment='Whether the author has finished the action.\n    After this is set to True, no modifications are allowed.\n    By default actions are closed when performed.\n    '),
                    sa.Column('description', sa.Unicode(), nullable=False, comment='A comment about the action.'),
                    sa.Column('start_time', sa.TIMESTAMP(timezone=True), nullable=True, comment='When the action starts. For some actions like\n    reservations the time when they are available, for others like renting\n    when the renting starts.\n    '),
                    sa.Column('end_time', sa.TIMESTAMP(timezone=True), nullable=True, comment='When the action ends. For some actions like reservations\n    the time when they expire, for others like renting\n    the time the end rents. For punctual actions it is the time \n    they are performed; it differs with ``created`` in which\n    created is the where the system received the action.\n    '),
                    sa.Column('snapshot_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False, comment='The user that recorded this action in the system.\n     \n    This does not necessarily has to be the person that produced\n    the action in the real world. For that purpose see\n    ``agent``.\n    '),
                    sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False, comment='The direct performer or driver of the action. \n    e.g. John wrote a book.\n    \n    It can differ with the user that registered the action in the\n    system, which can be in their behalf.\n    '),
                    sa.Column('parent_id', sa.BigInteger(), nullable=True, comment='For actions that are performed to components, \n    the device parent at that time.\n    \n    For example: for a ``EraseBasic`` performed on a data storage, this\n    would point to the computer that contained this data storage, if any.\n    '),
                    sa.ForeignKeyConstraint(['agent_id'], [f'{get_inv()}.agent.id'], ),
                    sa.ForeignKeyConstraint(['author_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['parent_id'], [f'{get_inv()}.computer.id'], ),
                    sa.ForeignKeyConstraint(['snapshot_id'], [f'{get_inv()}.snapshot.id'], name='snapshot_actions', use_alter=True),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )
    op.create_index(op.f('ix_action_created'), 'action', ['created'], unique=False, schema=f'{get_inv()}')
    op.create_index(op.f('ix_action_updated'), 'action', ['updated'], unique=False, schema=f'{get_inv()}')
    op.create_index('ix_id', 'action', ['id'], unique=False, postgresql_using='hash', schema=f'{get_inv()}')
    op.create_index('ix_parent_id', 'action', ['parent_id'], unique=False, postgresql_using='hash', schema=f'{get_inv()}')
    op.create_index('ix_type', 'action', ['type'], unique=False, postgresql_using='hash', schema=f'{get_inv()}')

    # Component table
    op.create_table('component',
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.Column('parent_id', sa.BigInteger(), nullable=True),
                    sa.Column('focal_length', sa.SmallInteger(), nullable=True),
                    sa.Column('video_height', sa.SmallInteger(), nullable=True),
                    sa.Column('video_width', sa.Integer(), nullable=True),
                    sa.Column('horizontal_view_angle', sa.Integer(), nullable=True),
                    sa.Column('facing', sa.Enum('Front', 'Back', name='camerafacing'), nullable=True),
                    sa.Column('vertical_view_angle', sa.SmallInteger(), nullable=True),
                    sa.Column('video_stabilization', sa.Boolean(), nullable=True),
                    sa.Column('flash', sa.Boolean(), nullable=True),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.device.id'], ),
                    sa.ForeignKeyConstraint(['parent_id'], [f'{get_inv()}.computer.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )
    op.create_index('parent_index', 'component', ['parent_id'], unique=False, postgresql_using='hash', schema=f'{get_inv()}')

    # Deliverynote table
    op.create_table('deliverynote',
                    sa.Column('updated', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='The last time Devicehub recorded a change for \n    this thing.\n    '),
                    sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='When Devicehub created this.'),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('document_id', citext.CIText(), nullable=False),
                    sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('supplier_email', citext.CIText(), nullable=False),
                    sa.Column('receiver_address', citext.CIText(), nullable=False),
                    sa.Column('date', sa.DateTime(), nullable=False, comment='The date the DeliveryNote initiated'),
                    sa.Column('deposit', sa.Integer(), nullable=True),
                    sa.Column('expected_devices', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
                    sa.Column('transferred_devices', sa.ARRAY(sa.Integer(), dimensions=1), nullable=True),
                    sa.Column('transfer_state', teal.db.IntEnum(TransferState), nullable=False, comment='State of transfer for a given Lot of devices.\n    '),
                    sa.Column('ethereum_address', citext.CIText(), nullable=True),
                    sa.Column('lot_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['creator_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['lot_id'], [f'{get_inv()}.lot.id'], ),
                    sa.ForeignKeyConstraint(['receiver_address'], ['common.user.email'], ),
                    sa.ForeignKeyConstraint(['supplier_email'], ['common.user.email'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('ethereum_address'),
                    schema=f'{get_inv()}'
                    )
    op.create_index(op.f('ix_deliverynote_created'), 'deliverynote', ['created'], unique=False, schema=f'{get_inv()}')
    op.create_index(op.f('ix_deliverynote_updated'), 'deliverynote', ['updated'], unique=False, schema=f'{get_inv()}')

    # Individual table
    op.create_table('individual',
                    sa.Column('active_org_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['active_org_id'], [f'{get_inv()}.organization.id'], ),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.agent.id'], ),
                    sa.ForeignKeyConstraint(['user_id'], ['common.user.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('user_id'),
                    schema=f'{get_inv()}'
                    )

    # Lot device table
    op.create_table('lot_device',
                    sa.Column('device_id', sa.BigInteger(), nullable=False),
                    sa.Column('lot_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('created', sa.DateTime(), nullable=False),
                    sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False, comment='The user that put the device in the lot.'),
                    sa.ForeignKeyConstraint(['author_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['device_id'], [f'{get_inv()}.device.id'], ),
                    sa.ForeignKeyConstraint(['lot_id'], [f'{get_inv()}.lot.id'], ),
                    sa.PrimaryKeyConstraint('device_id', 'lot_id'),
                    schema=f'{get_inv()}'
                    )

    # Path table
    op.create_table('path',
                    sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
                    sa.Column('lot_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('path', sqlalchemy_utils.types.ltree.LtreeType(), nullable=False),
                    sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='When Devicehub created this.'),
                    sa.ForeignKeyConstraint(['lot_id'], [f'{get_inv()}.lot.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('path', deferrable='True', initially='immediate', name='path_unique'),
                    schema=f'{get_inv()}'
                    )
    op.create_index('lot_id_index', 'path', ['lot_id'], unique=False, postgresql_using='hash', schema=f'{get_inv()}')
    op.create_index('path_btree', 'path', ['path'], unique=False, postgresql_using='btree', schema=f'{get_inv()}')
    op.create_index('path_gist', 'path', ['path'], unique=False, postgresql_using='gist', schema=f'{get_inv()}')

    # Proof recycling table
    op.create_table('proof_recycling',
                    sa.Column('collection_point', citext.CIText(), nullable=False),
                    sa.Column('date', sa.DateTime(), nullable=False),
                    sa.Column('contact', citext.CIText(), nullable=False),
                    sa.Column('ticket', citext.CIText(), nullable=False),
                    sa.Column('gps_location', citext.CIText(), nullable=False),
                    sa.Column('recycler_code', citext.CIText(), nullable=False),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.proof.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Proof reuse table
    op.create_table('proof_reuse',
                    sa.Column('receiver_segment', citext.CIText(), nullable=False),
                    sa.Column('id_receipt', citext.CIText(), nullable=False),
                    sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('receiver_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('price', sa.Integer(), nullable=True),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.proof.id'], ),
                    sa.ForeignKeyConstraint(['receiver_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['supplier_id'], ['common.user.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Proof transfer table
    op.create_table('proof_transfer',
                    sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('receiver_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('deposit', sa.Integer(), nullable=True),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.proof.id'], ),
                    sa.ForeignKeyConstraint(['receiver_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['supplier_id'], ['common.user.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Tag table
    op.create_table('tag',
                    sa.Column('updated', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='The last time Devicehub recorded a change for \n    this thing.\n    '),
                    sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='When Devicehub created this.'),
                    sa.Column('id', citext.CIText(), nullable=False, comment='The ID of the tag.'),
                    sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('provider', teal.db.URL(), nullable=True, comment='The tag provider URL. If None, the provider is\n    this Devicehub.\n    '),
                    sa.Column('device_id', sa.BigInteger(), nullable=True),
                    sa.Column('secondary', citext.CIText(), nullable=True, comment='A secondary identifier for this tag. \n    It has the same constraints as the main one. Only needed in special cases.\n    '),
                    sa.ForeignKeyConstraint(['device_id'], [f'{get_inv()}.device.id'], ondelete='SET NULL'),
                    sa.ForeignKeyConstraint(['org_id'], [f'{get_inv()}.organization.id'], ),
                    sa.PrimaryKeyConstraint('id', 'org_id'),
                    sa.UniqueConstraint('id', 'org_id', name='one tag id per organization'),
                    sa.UniqueConstraint('secondary', 'org_id', name='one secondary tag per organization'),
                    schema=f'{get_inv()}'
                    )
    op.create_index('device_id_index', 'tag', ['device_id'], unique=False, postgresql_using='hash', schema=f'{get_inv()}')
    op.create_index(op.f('ix_tag_created'), 'tag', ['created'], unique=False, schema=f'{get_inv()}')
    op.create_index(op.f('ix_tag_secondary'), 'tag', ['secondary'], unique=False, schema=f'{get_inv()}')
    op.create_index(op.f('ix_tag_updated'), 'tag', ['updated'], unique=False, schema=f'{get_inv()}')

    # ActionComponent table
    op.create_table('action_component',
                    sa.Column('device_id', sa.BigInteger(), nullable=False),
                    sa.Column('action_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['action_id'], [f'{get_inv()}.action.id'], ),
                    sa.ForeignKeyConstraint(['device_id'], [f'{get_inv()}.component.id'], ),
                    sa.PrimaryKeyConstraint('device_id', 'action_id'),
                    schema=f'{get_inv()}'
                    )

    # Action device table
    op.create_table('action_device',
                    sa.Column('device_id', sa.BigInteger(), nullable=False),
                    sa.Column('action_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['action_id'], [f'{get_inv()}.action.id'], ),
                    sa.ForeignKeyConstraint(['device_id'], [f'{get_inv()}.device.id'], ),
                    sa.PrimaryKeyConstraint('device_id', 'action_id'),
                    schema=f'{get_inv()}'
                    )

    # ActionWithOneDevice table
    op.create_table('action_with_one_device',
                    sa.Column('device_id', sa.BigInteger(), nullable=False),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['device_id'], [f'{get_inv()}.device.id'], ),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )
    op.create_index('action_one_device_id_index', 'action_with_one_device', ['device_id'], unique=False, postgresql_using='hash', schema=f'{get_inv()}')

    # Allocate table
    op.create_table('allocate',
                    sa.Column('to_id', postgresql.UUID(), nullable=True),
                    sa.Column('organization', citext.CIText(), nullable=True),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
                    sa.ForeignKeyConstraint(['to_id'], ['common.user.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # BAtter table
    op.create_table('battery',
                    sa.Column('wireless', sa.Boolean(), nullable=True, comment='If the battery can be charged wirelessly.'),
                    sa.Column('technology', sa.Enum('LiIon', 'NiCd', 'NiMH', 'LiPoly', 'LiFe', 'LiMn', 'Al', name='batterytechnology'), nullable=True),
                    sa.Column('size', sa.Integer(), nullable=False, comment='Maximum battery capacity by design, in mAh.\n\n    Use BatteryTest\'s "size" to get the actual size of the battery.\n    '),
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.component.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # DataStorage table
    op.create_table('data_storage',
                    sa.Column('size', sa.Integer(), nullable=True, comment='The size of the data-storage in MB.'),
                    sa.Column('interface', sa.Enum('ATA', 'USB', 'PCI', name='datastorageinterface'), nullable=True),
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.component.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Deallocate table
    op.create_table('deallocate',
                    sa.Column('from_id', postgresql.UUID(), nullable=True),
                    sa.Column('organization', citext.CIText(), nullable=True),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['from_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Display table
    op.create_table('display',
                    sa.Column('size', sa.Float(decimal_return_scale=1), nullable=False, comment='The size of the monitor in inches.'),
                    sa.Column('technology', sa.Enum('CRT', 'TFT', 'LED', 'PDP', 'LCD', 'OLED', 'AMOLED', name='displaytech'), nullable=True, comment='The technology the monitor uses to display\n    the image.\n    '),
                    sa.Column('resolution_width', sa.SmallInteger(), nullable=False, comment='The maximum horizontal resolution the\n    monitor can natively support in pixels.\n    '),
                    sa.Column('resolution_height', sa.SmallInteger(), nullable=False, comment='The maximum vertical resolution the\n    monitor can natively support in pixels.\n    '),
                    sa.Column('refresh_rate', sa.SmallInteger(), nullable=True),
                    sa.Column('contrast_ratio', sa.SmallInteger(), nullable=True),
                    sa.Column('touchable', sa.Boolean(), nullable=True, comment='Whether it is a touchscreen.'),
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.component.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # GraphiCard table
    op.create_table('graphic_card',
                    sa.Column('memory', sa.SmallInteger(), nullable=True, comment='The amount of memory of the Graphic Card in MB.'),
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.component.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Membership table
    op.create_table('membership',
                    sa.Column('updated', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='The last time Devicehub recorded a change for \n    this thing.\n    '),
                    sa.Column('created', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='When Devicehub created this.'),
                    sa.Column('id', sa.Unicode(), nullable=True),
                    sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('individual_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['individual_id'], [f'{get_inv()}.individual.id'], ),
                    sa.ForeignKeyConstraint(['organization_id'], [f'{get_inv()}.organization.id'], ),
                    sa.PrimaryKeyConstraint('organization_id', 'individual_id'),
                    sa.UniqueConstraint('id', 'organization_id', name='One member id per organization.'),
                    schema=f'{get_inv()}'
                    )
    op.create_index(op.f('ix_membership_created'), 'membership', ['created'], unique=False, schema=f'{get_inv()}')
    op.create_index(op.f('ix_membership_updated'), 'membership', ['updated'], unique=False, schema=f'{get_inv()}')

    # Migrate table
    op.create_table('migrate',
                    sa.Column('other', teal.db.URL(), nullable=False, comment='\n        The URL of the Migrate in the other end.\n    '),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Motherboard table
    op.create_table('motherboard',
                    sa.Column('slots', sa.SmallInteger(), nullable=True, comment='PCI slots the motherboard has.'),
                    sa.Column('usb', sa.SmallInteger(), nullable=True),
                    sa.Column('firewire', sa.SmallInteger(), nullable=True),
                    sa.Column('serial', sa.SmallInteger(), nullable=True),
                    sa.Column('pcmcia', sa.SmallInteger(), nullable=True),
                    sa.Column('bios_date', sa.Date(), nullable=True, comment='The date of the BIOS version.'),
                    sa.Column('ram_slots', sa.SmallInteger(), nullable=True),
                    sa.Column('ram_max_size', sa.Integer(), nullable=True),
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.component.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Network adapter
    op.create_table('network_adapter',
                    sa.Column('speed', sa.SmallInteger(), nullable=True, comment='The maximum speed this network adapter can handle,\n    in mbps.\n    '),
                    sa.Column('wireless', sa.Boolean(), nullable=False, comment='Whether it is a wireless interface.'),
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.component.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Organize table
    op.create_table('organize',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Processor table
    op.create_table('processor',
                    sa.Column('speed', sa.Float(), nullable=True, comment='The regular CPU speed.'),
                    sa.Column('cores', sa.SmallInteger(), nullable=True, comment='The number of regular cores.'),
                    sa.Column('threads', sa.SmallInteger(), nullable=True, comment='The number of threads per core.'),
                    sa.Column('address', sa.SmallInteger(), nullable=True, comment='The address of the CPU: 8, 16, 32, 64, 128 or 256 bits.'),
                    sa.Column('abi', sa.Unicode(), nullable=True, comment='The Application Binary Interface of the processor.'),
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.component.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # RamModule table
    op.create_table('ram_module',
                    sa.Column('size', sa.SmallInteger(), nullable=True, comment='The capacity of the RAM stick.'),
                    sa.Column('speed', sa.SmallInteger(), nullable=True),
                    sa.Column('interface', sa.Enum('SDRAM', 'DDR', 'DDR2', 'DDR3', 'DDR4', 'DDR5', 'DDR6', name='raminterface'), nullable=True),
                    sa.Column('format', sa.Enum('DIMM', 'SODIMM', name='ramformat'), nullable=True),
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.component.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Receive table
    op.create_table('receive',
                    sa.Column('role', sa.Enum('Intermediary', 'FinalUser', 'CollectionPoint', 'RecyclingPoint', 'Transporter', name='receiverrole'), nullable=False),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Sound card table
    op.create_table('sound_card',
                    sa.Column('id', sa.BigInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.component.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Benchmark table
    op.create_table('benchmark',
                    sa.Column('elapsed', sa.Interval(), nullable=True),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action_with_one_device.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Erase basic table
    op.create_table('erase_basic',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('method', sa.Enum('Shred', 'Disintegration', name='physicalerasuremethod'), nullable=True),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action_with_one_device.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    op.create_table('install',
                    sa.Column('elapsed', sa.Interval(), nullable=False),
                    sa.Column('address', sa.SmallInteger(), nullable=True),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action_with_one_device.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Live table
    op.create_table('live',
                    sa.Column('ip', teal.db.IP(), nullable=False, comment='The IP where the live was triggered.'),
                    sa.Column('subdivision_confidence', sa.SmallInteger(), nullable=False),
                    sa.Column('subdivision', sa.Enum('AE-AJ', 'AE-AZ', 'AE-DU', 'AE-FU', 'AE-RK', 'AE-SH', 'AE-UQ', 'AF-BAL', 'AF-BAM', 'AF-BDG', 'AF-BDS', 'AF-BGL', 'AF-FRAU', 'AF-FYB', 'AF-GHA', 'AF-GHO', 'AF-HEL', 'AF-HER', 'AF-JOW', 'AF-KAB', 'AF-KANN', 'AF-KAP', 'AF-KDZ', 'AF-KNR', 'AF-LAG', 'AF-LOW', 'AF-NAN', 'AF-NIM', 'AF-ORU', 'AF-PAR', 'AF-PIA', 'AF-PKA', 'AF-SAM', 'AF-SAR', 'AF-TAK', 'AF-WAR', 'AF-ZAB', 'AL-BR', 'AL-BU', 'AL-DI', 'AL-DL', 'AL-DR', 'AL-DV', 'AL-EL', 'AL-ER', 'AL-FR', 'AL-GJ', 'AL-GR', 'AL-HA', 'AL-KA', 'AL-KB', 'AL-KC', 'AL-KO', 'AL-KR', 'AL-KU', 'AL-LA', 'AL-LB', 'AL-LE', 'AL-LU', 'AL-MK', 'AL-MM', 'AL-MR', 'AL-MT', 'AL-PG', 'AL-PQ', 'AL-PR', 'AL-PU', 'AL-SH', 'AL-SK', 'AL-SR', 'AL-TE', 'AL-TP', 'AL-TR', 'AL-VL', 'AM-AG', 'AM-AR', 'AM-AV', 'AM-ER', 'AM-GR', 'AM-KT', 'AM-LO', 'AM-SH', 'AM-SU', 'AM-TV', 'AM-VD', 'AO-BGO', 'AO-BGU', 'AO-BIE', 'AO-CAB', 'AO-CCU', 'AO-CNN', 'AO-CNO', 'AO-CUS', 'AO-HUA', 'AO-HUI', 'AO-LNO', 'AO-LSU', 'AO-LUA', 'AO-MAL', 'AO-MOX', 'AO-NAM', 'AO-UIG', 'AO-ZAI', 'AR-A', 'AR-B', 'AR-C', 'AR-D', 'AR-E', 'AR-F', 'AR-G', 'AR-H', 'AR-J', 'AR-K', 'AR-L', 'AR-M', 'AR-N', 'AR-P', 'AR-Q', 'AR-R', 'AR-S', 'AR-T', 'AR-U', 'AR-V', 'AR-W', 'AR-X', 'AR-Y', 'AR-Z', 'AT-1', 'AT-2', 'AT-3', 'AT-4', 'AT-5', 'AT-6', 'AT-7', 'AT-8', 'AT-9', 'AU-CT', 'AU-NS', 'AU-NT', 'AU-QL', 'AU-SA', 'AU-TS', 'AU-VI', 'AU-WA', 'AZ-AB', 'AZ-ABS', 'AZ-AGA', 'AZ-AGC', 'AZ-AGM', 'AZ-AGS', 'AZ-AGU', 'AZ-AST', 'AZ-BA', 'AZ-BAB', 'AZ-BAL', 'AZ-BAR', 'AZ-BEY', 'AZ-BIL', 'AZ-CAB', 'AZ-CAL', 'AZ-CUL', 'AZ-DAS', 'AZ-DAV', 'AZ-FUZ', 'AZ-GA', 'AZ-GAD', 'AZ-GOR', 'AZ-GOY', 'AZ-HAC', 'AZ-IMI', 'AZ-ISM', 'AZ-KAL', 'AZ-KUR', 'AZ-LA', 'AZ-LAC', 'AZ-LAN', 'AZ-LER', 'AZ-MAS', 'AZ-MI', 'AZ-MM', 'AZ-NA', 'AZ-NEF', 'AZ-OGU', 'AZ-ORD', 'AZ-QAB', 'AZ-QAX', 'AZ-QAZ', 'AZ-QBA', 'AZ-QBI', 'AZ-QOB', 'AZ-QUS', 'AZ-SA', 'AZ-SAB', 'AZ-SAD', 'AZ-SAH', 'AZ-SAK', 'AZ-SAL', 'AZ-SAR', 'AZ-SAT', 'AZ-SIY', 'AZ-SKR', 'AZ-SM', 'AZ-SMI', 'AZ-SMX', 'AZ-SS', 'AZ-SUS', 'AZ-TAR', 'AZ-TOV', 'AZ-UCA', 'AZ-XA', 'AZ-XAC', 'AZ-XAN', 'AZ-XCI', 'AZ-XIZ', 'AZ-XVD', 'AZ-YAR', 'AZ-YE', 'AZ-YEV', 'AZ-ZAN', 'AZ-ZAQ', 'AZ-ZAR', 'BA-BIH', 'BA-SRP', 'BD-01', 'BD-02', 'BD-03', 'BD-04', 'BD-05', 'BD-06', 'BD-07', 'BD-08', 'BD-09', 'BD-1', 'BD-10', 'BD-11', 'BD-12', 'BD-13', 'BD-14', 'BD-15', 'BD-16', 'BD-17', 'BD-18', 'BD-19', 'BD-2', 'BD-20', 'BD-21', 'BD-22', 'BD-23', 'BD-24', 'BD-25', 'BD-26', 'BD-27', 'BD-28', 'BD-29', 'BD-3', 'BD-30', 'BD-31', 'BD-32', 'BD-33', 'BD-34', 'BD-35', 'BD-36', 'BD-37', 'BD-38', 'BD-39', 'BD-4', 'BD-40', 'BD-41', 'BD-42', 'BD-43', 'BD-44', 'BD-45', 'BD-46', 'BD-47', 'BD-48', 'BD-49', 'BD-5', 'BD-50', 'BD-51', 'BD-52', 'BD-53', 'BD-54', 'BD-55', 'BD-56', 'BD-57', 'BD-58', 'BD-59', 'BD-6', 'BD-60', 'BD-61', 'BD-62', 'BD-63', 'BD-64', 'BE-BRU', 'BE-VAN', 'BE-VBR', 'BE-VLG', 'BE-VLI', 'BE-VOV', 'BE-VWV', 'BE-WAL', 'BE-WBR', 'BE-WHT', 'BE-WLG', 'BE-WLX', 'BE-WNA', 'BF-BAL', 'BF-BAM', 'BF-BAN', 'BF-BAZ', 'BF-BGR', 'BF-BLG', 'BF-BLK', 'BF-COM', 'BF-GAN', 'BF-GNA', 'BF-GOU', 'BF-HOU', 'BF-IOB', 'BF-KAD', 'BF-KEN', 'BF-KMD', 'BF-KMP', 'BF-KOP', 'BF-KOS', 'BF-KOT', 'BF-KOW', 'BF-LER', 'BF-LOR', 'BF-MOU', 'BF-NAM', 'BF-NAO', 'BF-NAY', 'BF-NOU', 'BF-OUB', 'BF-OUD', 'BF-PAS', 'BF-PON', 'BF-SEN', 'BF-SIS', 'BF-SMT', 'BF-SNG', 'BF-SOM', 'BF-SOR', 'BF-TAP', 'BF-TUI', 'BF-YAG', 'BF-YAT', 'BF-ZIR', 'BF-ZON', 'BF-ZOU', 'BG-01', 'BG-02', 'BG-03', 'BG-04', 'BG-05', 'BG-06', 'BG-07', 'BG-08', 'BG-09', 'BG-10', 'BG-11', 'BG-12', 'BG-13', 'BG-14', 'BG-15', 'BG-16', 'BG-17', 'BG-18', 'BG-19', 'BG-20', 'BG-21', 'BG-22', 'BG-23', 'BG-24', 'BG-25', 'BG-26', 'BG-27', 'BG-28', 'BH-01', 'BH-02', 'BH-03', 'BH-04', 'BH-05', 'BH-06', 'BH-07', 'BH-08', 'BH-09', 'BH-10', 'BH-11', 'BH-12', 'BI-BB', 'BI-BJ', 'BI-BR', 'BI-CA', 'BI-CI', 'BI-GI', 'BI-KI', 'BI-KR', 'BI-KY', 'BI-MA', 'BI-MU', 'BI-MW', 'BI-MY', 'BI-NG', 'BI-RT', 'BI-RY', 'BJ-AK', 'BJ-AL', 'BJ-AQ', 'BJ-BO', 'BJ-CO', 'BJ-DO', 'BJ-KO', 'BJ-LI', 'BJ-MO', 'BJ-OU', 'BJ-PL', 'BJ-ZO', 'BN-BE', 'BN-BM', 'BN-TE', 'BN-TU', 'BO-B', 'BO-C', 'BO-H', 'BO-L', 'BO-N', 'BO-O', 'BO-P', 'BO-S', 'BO-T', 'BR-AC', 'BR-AL', 'BR-AM', 'BR-AP', 'BR-BA', 'BR-CE', 'BR-DF', 'BR-ES', 'BR-GO', 'BR-MA', 'BR-MG', 'BR-MS', 'BR-MT', 'BR-PA', 'BR-PB', 'BR-PE', 'BR-PI', 'BR-PR', 'BR-RJ', 'BR-RN', 'BR-RO', 'BR-RR', 'BR-RS', 'BR-SC', 'BR-SE', 'BR-SP', 'BR-TO', 'BS-AC', 'BS-BI', 'BS-CI', 'BS-EX', 'BS-FC', 'BS-FP', 'BS-GH', 'BS-GT', 'BS-HI', 'BS-HR', 'BS-IN', 'BS-KB', 'BS-LI', 'BS-MG', 'BS-MH', 'BS-NB', 'BS-NP', 'BS-RI', 'BS-RS', 'BS-SP', 'BS-SR', 'BT-11', 'BT-12', 'BT-13', 'BT-14', 'BT-15', 'BT-21', 'BT-22', 'BT-23', 'BT-24', 'BT-31', 'BT-32', 'BT-33', 'BT-34', 'BT-41', 'BT-42', 'BT-43', 'BT-44', 'BT-45', 'BT-GA', 'BT-TY', 'BW-CE', 'BW-CH', 'BW-GH', 'BW-KG', 'BW-KL', 'BW-KW', 'BW-NE', 'BW-NG', 'BW-SE', 'BW-SO', 'BY-BR', 'BY-HO', 'BY-HR', 'BY-MA', 'BY-MI', 'BY-VI', 'BZ-BZ', 'BZ-CY', 'BZ-CZL', 'BZ-OW', 'BZ-SC', 'BZ-TOL', 'CA-AB', 'CA-BC', 'CA-MB', 'CA-NB', 'CA-NL', 'CA-NS', 'CA-NT', 'CA-NU', 'CA-ON', 'CA-PE', 'CA-QC', 'CA-SK', 'CA-YT', 'CD-BC', 'CD-BN', 'CD-EQ', 'CD-KA', 'CD-KE', 'CD-KN', 'CD-KW', 'CD-MA', 'CD-NK', 'CD-OR', 'CD-SK', 'CF-AC', 'CF-BB', 'CF-BGF', 'CF-BK', 'CF-HK', 'CF-HM', 'CF-HS', 'CF-KB', 'CF-KG', 'CF-LB', 'CF-MB', 'CF-MP', 'CF-NM', 'CF-OP', 'CF-SE', 'CF-UK', 'CF-VK', 'CG-11', 'CG-12', 'CG-13', 'CG-14', 'CG-15', 'CG-2', 'CG-5', 'CG-7', 'CG-8', 'CG-9', 'CG-BZV', 'CH-AG', 'CH-AI', 'CH-AR', 'CH-BE', 'CH-BL', 'CH-BS', 'CH-FR', 'CH-GE', 'CH-GL', 'CH-GR', 'CH-JU', 'CH-LU', 'CH-NE', 'CH-NW', 'CH-OW', 'CH-SG', 'CH-SH', 'CH-SO', 'CH-SZ', 'CH-TG', 'CH-TI', 'CH-UR', 'CH-VD', 'CH-VS', 'CH-ZG', 'CH-ZH', 'CI-01', 'CI-02', 'CI-03', 'CI-04', 'CI-05', 'CI-06', 'CI-07', 'CI-08', 'CI-09', 'CI-10', 'CI-11', 'CI-12', 'CI-13', 'CI-14', 'CI-15', 'CI-16', 'CL-AI', 'CL-AN', 'CL-AR', 'CL-AT', 'CL-BI', 'CL-CO', 'CL-LI', 'CL-LL', 'CL-MA', 'CL-ML', 'CL-RM', 'CL-TA', 'CL-VS', 'CM-AD', 'CM-CE', 'CM-EN', 'CM-ES', 'CM-LT', 'CM-NO', 'CM-NW', 'CM-OU', 'CM-SU', 'CM-SW', 'CN-11', 'CN-12', 'CN-13', 'CN-14', 'CN-15', 'CN-21', 'CN-22', 'CN-23', 'CN-31', 'CN-32', 'CN-33', 'CN-34', 'CN-35', 'CN-36', 'CN-37', 'CN-41', 'CN-42', 'CN-43', 'CN-44', 'CN-45', 'CN-46', 'CN-50', 'CN-51', 'CN-52', 'CN-53', 'CN-54', 'CN-61', 'CN-62', 'CN-63', 'CN-64', 'CN-65', 'CN-71', 'CN-91', 'CN-92', 'CO-AMA', 'CO-ANT', 'CO-ARA', 'CO-ATL', 'CO-BOL', 'CO-BOY', 'CO-CAL', 'CO-CAQ', 'CO-CAS', 'CO-CAU', 'CO-CES', 'CO-CHO', 'CO-COR', 'CO-CUN', 'CO-DC', 'CO-GUA', 'CO-GUV', 'CO-HUI', 'CO-LAG', 'CO-MAG', 'CO-MET', 'CO-NAR', 'CO-NSA', 'CO-PUT', 'CO-QUI', 'CO-RIS', 'CO-SAN', 'CO-SAP', 'CO-SUC', 'CO-TOL', 'CO-VAC', 'CO-VAU', 'CO-VID', 'CR-A', 'CR-C', 'CR-G', 'CR-H', 'CR-L', 'CR-P', 'CR-SJ', 'CU-01', 'CU-02', 'CU-03', 'CU-04', 'CU-05', 'CU-06', 'CU-07', 'CU-08', 'CU-09', 'CU-10', 'CU-11', 'CU-12', 'CU-13', 'CU-14', 'CU-99', 'CV-B', 'CV-BR', 'CV-BV', 'CV-CA', 'CV-CR', 'CV-CS', 'CV-FO', 'CV-MA', 'CV-MO', 'CV-PA', 'CV-PN', 'CV-PR', 'CV-RG', 'CV-S', 'CV-SF', 'CV-SL', 'CV-SN', 'CV-SV', 'CV-TA', 'CY-01', 'CY-02', 'CY-03', 'CY-04', 'CY-05', 'CY-06', 'CZ-JC', 'CZ-JM', 'CZ-KA', 'CZ-KR', 'CZ-LI', 'CZ-MO', 'CZ-OL', 'CZ-PA', 'CZ-PL', 'CZ-PR', 'CZ-ST', 'CZ-US', 'CZ-VY', 'CZ-ZL', 'DE-BB', 'DE-BE', 'DE-BW', 'DE-BY', 'DE-HB', 'DE-HE', 'DE-HH', 'DE-MV', 'DE-NI', 'DE-NW', 'DE-RP', 'DE-SH', 'DE-SL', 'DE-SN', 'DE-ST', 'DE-TH', 'DJ-AS', 'DJ-DI', 'DJ-DJ', 'DJ-OB', 'DJ-TA', 'DK-015', 'DK-020', 'DK-025', 'DK-030', 'DK-035', 'DK-040', 'DK-042', 'DK-050', 'DK-055', 'DK-060', 'DK-065', 'DK-070', 'DK-076', 'DK-080', 'DK-101', 'DK-147', 'DO-01', 'DO-02', 'DO-03', 'DO-04', 'DO-05', 'DO-06', 'DO-07', 'DO-08', 'DO-09', 'DO-10', 'DO-11', 'DO-12', 'DO-13', 'DO-14', 'DO-15', 'DO-16', 'DO-17', 'DO-18', 'DO-19', 'DO-20', 'DO-21', 'DO-22', 'DO-23', 'DO-24', 'DO-25', 'DO-26', 'DO-27', 'DO-28', 'DO-29', 'DO-30', 'DZ-01', 'DZ-02', 'DZ-03', 'DZ-04', 'DZ-05', 'DZ-06', 'DZ-07', 'DZ-08', 'DZ-09', 'DZ-10', 'DZ-11', 'DZ-12', 'DZ-13', 'DZ-14', 'DZ-15', 'DZ-16', 'DZ-17', 'DZ-18', 'DZ-19', 'DZ-20', 'DZ-21', 'DZ-22', 'DZ-23', 'DZ-24', 'DZ-25', 'DZ-26', 'DZ-27', 'DZ-28', 'DZ-29', 'DZ-30', 'DZ-31', 'DZ-32', 'DZ-33', 'DZ-34', 'DZ-35', 'DZ-36', 'DZ-37', 'DZ-38', 'DZ-39', 'DZ-40', 'DZ-41', 'DZ-42', 'DZ-43', 'DZ-44', 'DZ-45', 'DZ-46', 'DZ-47', 'DZ-48', 'EC-A', 'EC-B', 'EC-C', 'EC-D', 'EC-E', 'EC-F', 'EC-G', 'EC-H', 'EC-I', 'EC-L', 'EC-M', 'EC-N', 'EC-O', 'EC-P', 'EC-R', 'EC-S', 'EC-T', 'EC-U', 'EC-W', 'EC-X', 'EC-Y', 'EC-Z', 'EE-37', 'EE-39', 'EE-44', 'EE-49', 'EE-51', 'EE-57', 'EE-59', 'EE-65', 'EE-67', 'EE-70', 'EE-74', 'EE-78', 'EE-82', 'EE-84', 'EE-86', 'EG-ALX', 'EG-ASN', 'EG-AST', 'EG-BA', 'EG-BH', 'EG-BNS', 'EG-C', 'EG-DK', 'EG-DT', 'EG-FYM', 'EG-GH', 'EG-GZ', 'EG-IS', 'EG-JS', 'EG-KB', 'EG-KFS', 'EG-KN', 'EG-MN', 'EG-MNF', 'EG-MT', 'EG-PTS', 'EG-SHG', 'EG-SHR', 'EG-SIN', 'EG-SUZ', 'EG-WAD', 'ER-AN', 'ER-DK', 'ER-DU', 'ER-GB', 'ER-MA', 'ER-SK', 'ES-A', 'ES-AB', 'ES-AL', 'ES-AN', 'ES-AR', 'ES-AV', 'ES-B', 'ES-BA', 'ES-BI', 'ES-BU', 'ES-C', 'ES-CA', 'ES-CC', 'ES-CE', 'ES-CL', 'ES-CM', 'ES-CN', 'ES-CO', 'ES-CR', 'ES-CS', 'ES-CT', 'ES-CU', 'ES-EX', 'ES-GA', 'ES-GC', 'ES-GI', 'ES-GR', 'ES-GU', 'ES-H', 'ES-HU', 'ES-J', 'ES-L', 'ES-LE', 'ES-LO', 'ES-LU', 'ES-M', 'ES-MA', 'ES-ML', 'ES-MU', 'ES-NA', 'ES-O', 'ES-OR', 'ES-P', 'ES-PM', 'ES-PO', 'ES-PV', 'ES-S', 'ES-SA', 'ES-SE', 'ES-SG', 'ES-SO', 'ES-SS', 'ES-T', 'ES-TE', 'ES-TF', 'ES-TO', 'ES-V', 'ES-VA', 'ES-VC', 'ES-VI', 'ES-Z', 'ES-ZA', 'ET-AA', 'ET-AF', 'ET-AM', 'ET-BE', 'ET-DD', 'ET-GA', 'ET-HA', 'ET-OR', 'ET-SN', 'ET-SO', 'ET-TI', 'FI-AL', 'FI-ES', 'FI-IS', 'FI-LL', 'FI-LS', 'FI-OL', 'FJ-C', 'FJ-E', 'FJ-N', 'FJ-R', 'FJ-W', 'FM-KSA', 'FM-PNI', 'FM-TRK', 'FM-YAP', 'FR-01', 'FR-02', 'FR-03', 'FR-04', 'FR-05', 'FR-06', 'FR-07', 'FR-08', 'FR-09', 'FR-10', 'FR-11', 'FR-12', 'FR-13', 'FR-14', 'FR-15', 'FR-16', 'FR-17', 'FR-18', 'FR-19', 'FR-21', 'FR-22', 'FR-23', 'FR-24', 'FR-25', 'FR-26', 'FR-27', 'FR-28', 'FR-29', 'FR-2A', 'FR-2B', 'FR-30', 'FR-31', 'FR-32', 'FR-33', 'FR-34', 'FR-35', 'FR-36', 'FR-37', 'FR-38', 'FR-39', 'FR-40', 'FR-41', 'FR-42', 'FR-43', 'FR-44', 'FR-45', 'FR-46', 'FR-47', 'FR-48', 'FR-49', 'FR-50', 'FR-51', 'FR-52', 'FR-53', 'FR-54', 'FR-55', 'FR-56', 'FR-57', 'FR-58', 'FR-59', 'FR-60', 'FR-61', 'FR-62', 'FR-63', 'FR-64', 'FR-65', 'FR-66', 'FR-67', 'FR-68', 'FR-69', 'FR-70', 'FR-71', 'FR-72', 'FR-73', 'FR-74', 'FR-75', 'FR-76', 'FR-77', 'FR-78', 'FR-79', 'FR-80', 'FR-81', 'FR-82', 'FR-83', 'FR-84', 'FR-85', 'FR-86', 'FR-87', 'FR-88', 'FR-89', 'FR-90', 'FR-91', 'FR-92', 'FR-93', 'FR-94', 'FR-95', 'FR-A', 'FR-B', 'FR-C', 'FR-D', 'FR-E', 'FR-F', 'FR-G', 'FR-GF', 'FR-GP', 'FR-H', 'FR-I', 'FR-J', 'FR-K', 'FR-L', 'FR-M', 'FR-MQ', 'FR-N', 'FR-NC', 'FR-O', 'FR-P', 'FR-PF', 'FR-PM', 'FR-Q', 'FR-R', 'FR-RE', 'FR-S', 'FR-T', 'FR-TF', 'FR-U', 'FR-V', 'FR-WF', 'FR-YT', 'GA-1', 'GA-2', 'GA-3', 'GA-4', 'GA-5', 'GA-6', 'GA-7', 'GA-8', 'GA-9', 'GB-ABD', 'GB-ABE', 'GB-AGB', 'GB-AGY', 'GB-ANS', 'GB-ANT', 'GB-ARD', 'GB-ARM', 'GB-BAS', 'GB-BBD', 'GB-BDF', 'GB-BDG', 'GB-BEN', 'GB-BEX', 'GB-BFS', 'GB-BGE', 'GB-BGW', 'GB-BIR', 'GB-BKM', 'GB-BLA', 'GB-BLY', 'GB-BMH', 'GB-BNB', 'GB-BNE', 'GB-BNH', 'GB-BNS', 'GB-BOL', 'GB-BPL', 'GB-BRC', 'GB-BRD', 'GB-BRY', 'GB-BST', 'GB-BUR', 'GB-CAM', 'GB-CAY', 'GB-CGN', 'GB-CGV', 'GB-CHA', 'GB-CHS', 'GB-CKF', 'GB-CKT', 'GB-CLD', 'GB-CLK', 'GB-CLR', 'GB-CMA', 'GB-CMD', 'GB-CMN', 'GB-CON', 'GB-COV', 'GB-CRF', 'GB-CRY', 'GB-CSR', 'GB-CWY', 'GB-DAL', 'GB-DBY', 'GB-DEN', 'GB-DER', 'GB-DEV', 'GB-DGN', 'GB-DGY', 'GB-DNC', 'GB-DND', 'GB-DOR', 'GB-DOW', 'GB-DRY', 'GB-DUD', 'GB-DUR', 'GB-EAL', 'GB-EAW', 'GB-EAY', 'GB-EDH', 'GB-EDU', 'GB-ELN', 'GB-ELS', 'GB-ENF', 'GB-ENG', 'GB-ERW', 'GB-ERY', 'GB-ESS', 'GB-ESX', 'GB-FAL', 'GB-FER', 'GB-FIF', 'GB-FLN', 'GB-GAT', 'GB-GBN', 'GB-GLG', 'GB-GLS', 'GB-GRE', 'GB-GSY', 'GB-GWN', 'GB-HAL', 'GB-HAM', 'GB-HAV', 'GB-HCK', 'GB-HEF', 'GB-HIL', 'GB-HLD', 'GB-HMF', 'GB-HNS', 'GB-HPL', 'GB-HRT', 'GB-HRW', 'GB-HRY', 'GB-IOM', 'GB-IOS', 'GB-IOW', 'GB-ISL', 'GB-IVC', 'GB-JSY', 'GB-KEC', 'GB-KEN', 'GB-KHL', 'GB-KIR', 'GB-KTT', 'GB-KWL', 'GB-LAN', 'GB-LBH', 'GB-LCE', 'GB-LDS', 'GB-LEC', 'GB-LEW', 'GB-LIN', 'GB-LIV', 'GB-LMV', 'GB-LND', 'GB-LRN', 'GB-LSB', 'GB-LUT', 'GB-MAN', 'GB-MDB', 'GB-MDW', 'GB-MFT', 'GB-MIK', 'GB-MLN', 'GB-MON', 'GB-MRT', 'GB-MRY', 'GB-MTY', 'GB-MYL', 'GB-NAY', 'GB-NBL', 'GB-NDN', 'GB-NEL', 'GB-NET', 'GB-NFK', 'GB-NGM', 'GB-NIR', 'GB-NLK', 'GB-NLN', 'GB-NSM', 'GB-NTA', 'GB-NTH', 'GB-NTL', 'GB-NTT', 'GB-NTY', 'GB-NWM', 'GB-NWP', 'GB-NYK', 'GB-NYM', 'GB-OLD', 'GB-OMH', 'GB-ORK', 'GB-OXF', 'GB-PEM', 'GB-PKN', 'GB-PLY', 'GB-POL', 'GB-POR', 'GB-POW', 'GB-PTE', 'GB-RCC', 'GB-RCH', 'GB-RCT', 'GB-RDB', 'GB-RDG', 'GB-RFW', 'GB-RIC', 'GB-ROT', 'GB-RUT', 'GB-SAW', 'GB-SAY', 'GB-SCB', 'GB-SCT', 'GB-SFK', 'GB-SFT', 'GB-SGC', 'GB-SHF', 'GB-SHN', 'GB-SHR', 'GB-SKP', 'GB-SLF', 'GB-SLG', 'GB-SLK', 'GB-SND', 'GB-SOL', 'GB-SOM', 'GB-SOS', 'GB-SRY', 'GB-STB', 'GB-STE', 'GB-STG', 'GB-STH', 'GB-STN', 'GB-STS', 'GB-STT', 'GB-STY', 'GB-SWA', 'GB-SWD', 'GB-SWK', 'GB-TAM', 'GB-TFW', 'GB-THR', 'GB-TOB', 'GB-TOF', 'GB-TRF', 'GB-TWH', 'GB-UKM', 'GB-VGL', 'GB-WAR', 'GB-WBK', 'GB-WDU', 'GB-WFT', 'GB-WGN', 'GB-WILL', 'GB-WKF', 'GB-WLL', 'GB-WLN', 'GB-WLS', 'GB-WLV', 'GB-WND', 'GB-WNM', 'GB-WOK', 'GB-WOR', 'GB-WRL', 'GB-WRT', 'GB-WRX', 'GB-WSM', 'GB-WSX', 'GB-YOR', 'GB-ZET', 'GE-AB', 'GE-AJ', 'GE-GU', 'GE-IM', 'GE-KA', 'GE-KK', 'GE-MM', 'GE-RL', 'GE-SJ', 'GE-SK', 'GE-SZ', 'GE-TB', 'GH-AA', 'GH-AH', 'GH-BA', 'GH-CP', 'GH-EP', 'GH-NP', 'GH-TV', 'GH-UE', 'GH-UW', 'GH-WP', 'GM-B', 'GM-L', 'GM-M', 'GM-N', 'GM-U', 'GM-W', 'GN-B', 'GN-BE', 'GN-BF', 'GN-BK', 'GN-C', 'GN-CO', 'GN-D', 'GN-DB', 'GN-DI', 'GN-DL', 'GN-DU', 'GN-F', 'GN-FA', 'GN-FO', 'GN-FR', 'GN-GA', 'GN-GU', 'GN-K', 'GN-KA', 'GN-KB', 'GN-KD; 2', 'GN-KE', 'GN-KN', 'GN-KO', 'GN-KS', 'GN-L', 'GN-LA', 'GN-LE', 'GN-LO', 'GN-M', 'GN-MC', 'GN-MD', 'GN-ML', 'GN-MM', 'GN-N', 'GN-NZ', 'GN-PI', 'GN-SI', 'GN-TE', 'GN-TO', 'GN-YO', 'GQ-AN', 'GQ-BN', 'GQ-BS', 'GQ-C', 'GQ-CS', 'GQ-I', 'GQ-KN', 'GQ-LI', 'GQ-WN', 'GR-01', 'GR-03', 'GR-04', 'GR-05', 'GR-06', 'GR-07', 'GR-11', 'GR-12', 'GR-13', 'GR-14', 'GR-15', 'GR-16', 'GR-17', 'GR-21', 'GR-22', 'GR-23', 'GR-24', 'GR-31', 'GR-32', 'GR-33', 'GR-34', 'GR-41', 'GR-42', 'GR-43', 'GR-44', 'GR-51', 'GR-52', 'GR-53', 'GR-54', 'GR-55', 'GR-56', 'GR-57', 'GR-58', 'GR-59', 'GR-61', 'GR-62', 'GR-63', 'GR-64', 'GR-69', 'GR-71', 'GR-72', 'GR-73', 'GR-81', 'GR-82', 'GR-83', 'GR-84', 'GR-85', 'GR-91', 'GR-92', 'GR-93', 'GR-94', 'GR-A1', 'GR-I', 'GR-II', 'GR-III', 'GR-IV', 'GR-IX', 'GR-V', 'GR-VI', 'GR-VII', 'GR-VIII', 'GR-X', 'GR-XI', 'GR-XII', 'GR-XIII', 'GT-AV', 'GT-BV', 'GT-CM', 'GT-CQ', 'GT-ES', 'GT-GU', 'GT-HU', 'GT-IZ', 'GT-JA', 'GT-JU', 'GT-PE', 'GT-PR', 'GT-QC', 'GT-QZ', 'GT-RE', 'GT-SA', 'GT-SM', 'GT-SO', 'GT-SR', 'GT-SU', 'GT-TO', 'GT-ZA', 'GW-BA', 'GW-BL', 'GW-BM', 'GW-BS', 'GW-CA', 'GW-GA', 'GW-L', 'GW-N', 'GW-OI', 'GW-QU', 'GW-S', 'GW-TO', 'GY-BA', 'GY-CU', 'GY-DE', 'GY-EB', 'GY-ES', 'GY-MA', 'GY-PM', 'GY-PT', 'GY-UD', 'GY-UT', 'HN-AT', 'HN-CH', 'HN-CL', 'HN-CM', 'HN-CP', 'HN-CR', 'HN-EP', 'HN-FM', 'HN-GD', 'HN-IB', 'HN-IN', 'HN-LE', 'HN-LP', 'HN-OC', 'HN-OL', 'HN-SB', 'HN-VA', 'HN-YO', 'HR-01', 'HR-02', 'HR-03', 'HR-04', 'HR-05', 'HR-06', 'HR-07', 'HR-08', 'HR-09', 'HR-10', 'HR-11', 'HR-12', 'HR-13', 'HR-14', 'HR-15', 'HR-16', 'HR-17', 'HR-18', 'HR-19', 'HR-20', 'HR-21', 'HT-AR', 'HT-CE', 'HT-GA', 'HT-ND', 'HT-NE', 'HT-NO', 'HT-OU', 'HT-SD', 'HT-SE', 'HU-BA', 'HU-BC', 'HU-BE', 'HU-BK', 'HU-BU', 'HU-BZ', 'HU-CS', 'HU-DE', 'HU-DU', 'HU-EG', 'HU-FE', 'HU-GS', 'HU-GY', 'HU-HB', 'HU-HE', 'HU-HV', 'HU-JN', 'HU-KE', 'HU-KM', 'HU-KV', 'HU-MI', 'HU-NK', 'HU-NO', 'HU-NY', 'HU-PE', 'HU-PS', 'HU-SD', 'HU-SF', 'HU-SH', 'HU-SK', 'HU-SN', 'HU-SO', 'HU-SS', 'HU-ST', 'HU-SZ', 'HU-TB', 'HU-TO', 'HU-VA', 'HU-VE', 'HU-VM', 'HU-ZA', 'HU-ZE', 'ID-AC', 'ID-BA', 'ID-BB', 'ID-BE', 'ID-BT', 'ID-GO', 'ID-IJ', 'ID-JA', 'ID-JB', 'ID-JI', 'ID-JK', 'ID-JT', 'ID-JW', 'ID-KA', 'ID-KB', 'ID-KI', 'ID-KS', 'ID-KT', 'ID-LA', 'ID-MA', 'ID-MU', 'ID-NB', 'ID-NT', 'ID-NU', 'ID-PA', 'ID-RI', 'ID-SA', 'ID-SB', 'ID-SG', 'ID-SL', 'ID-SM', 'ID-SN', 'ID-SS', 'ID-ST', 'ID-SU', 'ID-YO', 'IE-C', 'IE-C; 2', 'IE-CE', 'IE-CN', 'IE-CW', 'IE-D', 'IE-DL', 'IE-G', 'IE-KE', 'IE-KK', 'IE-KY', 'IE-L', 'IE-LD', 'IE-LH', 'IE-LK', 'IE-LM', 'IE-LS', 'IE-M', 'IE-MH', 'IE-MN', 'IE-MO', 'IE-OY', 'IE-RN', 'IE-SO', 'IE-TA', 'IE-U', 'IE-WD', 'IE-WH', 'IE-WW', 'IE-WX', 'IL-D', 'IL-HA', 'IL-JM', 'IL-M', 'IL-TA', 'IL-Z', 'IN-AN', 'IN-AP', 'IN-AR', 'IN-AS', 'IN-BR', 'IN-CH', 'IN-CT', 'IN-DD', 'IN-DL', 'IN-DN', 'IN-GA', 'IN-GJ', 'IN-HP', 'IN-HR', 'IN-JH', 'IN-JK', 'IN-KA', 'IN-KL', 'IN-LD', 'IN-MH', 'IN-ML', 'IN-MN', 'IN-MP', 'IN-MZ', 'IN-NL', 'IN-OR', 'IN-PB', 'IN-PY', 'IN-RJ', 'IN-SK', 'IN-TN', 'IN-TR', 'IN-UL', 'IN-UP', 'IN-WB', 'IQ-AN', 'IQ-AR', 'IQ-BA', 'IQ-BB', 'IQ-BG', 'IQ-DA', 'IQ-DI', 'IQ-DQ', 'IQ-KA', 'IQ-MA', 'IQ-MU', 'IQ-NA', 'IQ-NI', 'IQ-QA', 'IQ-SD', 'IQ-SU', 'IQ-TS', 'IQ-WA', 'IR-01', 'IR-02', 'IR-03', 'IR-04', 'IR-05', 'IR-06', 'IR-07', 'IR-08', 'IR-09', 'IR-10', 'IR-11', 'IR-12', 'IR-13', 'IR-14', 'IR-15', 'IR-16', 'IR-17', 'IR-18', 'IR-19', 'IR-20', 'IR-21', 'IR-22', 'IR-23', 'IR-24', 'IR-25', 'IR-26', 'IR-27', 'IR-28', 'IS-0', 'IS-1', 'IS-2', 'IS-3', 'IS-4', 'IS-5', 'IS-6', 'IS-7', 'IS-8', 'IT-21', 'IT-23', 'IT-25', 'IT-32', 'IT-34', 'IT-36', 'IT-42', 'IT-45', 'IT-52', 'IT-55', 'IT-57', 'IT-62', 'IT-65', 'IT-67', 'IT-72', 'IT-75', 'IT-77', 'IT-78', 'IT-82', 'IT-88', 'IT-AG', 'IT-AL', 'IT-AN', 'IT-AO', 'IT-AP', 'IT-AQ', 'IT-AR', 'IT-AT', 'IT-AV', 'IT-BA', 'IT-BG', 'IT-BI', 'IT-BL', 'IT-BN', 'IT-BO', 'IT-BR', 'IT-BS', 'IT-BZ', 'IT-CA', 'IT-CB', 'IT-CE', 'IT-CH', 'IT-CL', 'IT-CN', 'IT-CO', 'IT-CR', 'IT-CS', 'IT-CT', 'IT-CZ', 'IT-DU', 'IT-EN', 'IT-FE', 'IT-FG', 'IT-FI', 'IT-FO', 'IT-FR', 'IT-GE', 'IT-GO', 'IT-GR', 'IT-IM', 'IT-IS', 'IT-KR', 'IT-LC', 'IT-LE', 'IT-LI', 'IT-LO', 'IT-LT', 'IT-LU', 'IT-MC', 'IT-ME', 'IT-MI', 'IT-MN', 'IT-MO', 'IT-MS', 'IT-MT', 'IT-NA', 'IT-NO', 'IT-NU', 'IT-OR', 'IT-PA', 'IT-PC', 'IT-PD', 'IT-PE', 'IT-PG', 'IT-PI', 'IT-PN', 'IT-PO', 'IT-PR', 'IT-PS', 'IT-PT', 'IT-PV', 'IT-PZ', 'IT-RA', 'IT-RC', 'IT-RE', 'IT-RG', 'IT-RI', 'IT-RM', 'IT-RN', 'IT-RO', 'IT-SA', 'IT-SI', 'IT-SO', 'IT-SP', 'IT-SR', 'IT-SS', 'IT-SV', 'IT-TA', 'IT-TE', 'IT-TN', 'IT-TO', 'IT-TP', 'IT-TR', 'IT-TS', 'IT-TV', 'IT-VA', 'IT-VB', 'IT-VC', 'IT-VE', 'IT-VI', 'IT-VR', 'IT-VT', 'IT-VV', 'JM-01', 'JM-02', 'JM-03', 'JM-04', 'JM-05', 'JM-06', 'JM-07', 'JM-08', 'JM-09', 'JM-10', 'JM-11', 'JM-12', 'JM-13', 'JM-14', 'JO-AJ', 'JO-AM', 'JO-AQ', 'JO-AT', 'JO-AZ', 'JO-BA', 'JO-IR', 'JO-JA', 'JO-KA', 'JO-MA', 'JO-MD', 'JO-MN', 'JP-01', 'JP-02', 'JP-03', 'JP-04', 'JP-05', 'JP-06', 'JP-07', 'JP-08', 'JP-09', 'JP-10', 'JP-11', 'JP-12', 'JP-13', 'JP-14', 'JP-15', 'JP-16', 'JP-17', 'JP-18', 'JP-19', 'JP-20', 'JP-21', 'JP-22', 'JP-23', 'JP-24', 'JP-25', 'JP-26', 'JP-27', 'JP-28', 'JP-29', 'JP-30', 'JP-31', 'JP-32', 'JP-33', 'JP-34', 'JP-35', 'JP-36', 'JP-37', 'JP-38', 'JP-39', 'JP-40', 'JP-41', 'JP-42', 'JP-43', 'JP-44', 'JP-45', 'JP-46', 'JP-47', 'KE-110', 'KE-200', 'KE-300', 'KE-400', 'KE-500', 'KE-600', 'KE-700', 'KE-900', 'KG-B', 'KG-C', 'KG-GB', 'KG-J', 'KG-N', 'KG-O', 'KG-T', 'KG-Y', 'KH-1', 'KH-10', 'KH-11', 'KH-12', 'KH-13', 'KH-14', 'KH-15', 'KH-16', 'KH-17', 'KH-18', 'KH-19', 'KH-2', 'KH-20', 'KH-21', 'KH-22', 'KH-23', 'KH-24', 'KH-3', 'KH-4', 'KH-5', 'KH-6', 'KH-7', 'KH-8', 'KH-9', 'KI-G', 'KI-L', 'KI-P', 'KM-A', 'KM-G', 'KM-M', 'KP-CHA', 'KP-HAB', 'KP-HAN', 'KP-HWB', 'KP-HWN', 'KP-KAE', 'KP-KAN', 'KP-NAJ', 'KP-NAM', 'KP-PYB', 'KP-PYN', 'KP-PYO', 'KP-YAN', 'KR-11', 'KR-26', 'KR-27', 'KR-28', 'KR-29', 'KR-30', 'KR-31', 'KR-41', 'KR-42', 'KR-43', 'KR-44', 'KR-45', 'KR-46', 'KR-47', 'KR-48', 'KR-49', 'KW-AH', 'KW-FA', 'KW-HA', 'KW-JA', 'KW-KU', 'KZ-AKM', 'KZ-AKT', 'KZ-ALA', 'KZ-ALM', 'KZ-AST', 'KZ-ATY', 'KZ-KAR', 'KZ-KUS', 'KZ-KZY', 'KZ-MAN', 'KZ-PAV', 'KZ-SEV', 'KZ-VOS', 'KZ-YUZ', 'KZ-ZAP', 'KZ-ZHA', 'LA-AT', 'LA-BK', 'LA-BL', 'LA-CH', 'LA-HO', 'LA-KH', 'LA-LM', 'LA-LP', 'LA-OU', 'LA-PH', 'LA-SL', 'LA-SV', 'LA-VI', 'LA-VT', 'LA-XA', 'LA-XE', 'LA-XI', 'LA-XN', 'LB-AS', 'LB-BA', 'LB-BI', 'LB-JA', 'LB-JL', 'LB-NA', 'LK-1', 'LK-11', 'LK-12', 'LK-13', 'LK-2', 'LK-21', 'LK-22', 'LK-23', 'LK-3', 'LK-31', 'LK-32', 'LK-33', 'LK-4', 'LK-41', 'LK-42', 'LK-43', 'LK-44', 'LK-45', 'LK-5', 'LK-51', 'LK-52', 'LK-53', 'LK-6', 'LK-61', 'LK-62', 'LK-7', 'LK-71', 'LK-72', 'LK-8', 'LK-81', 'LK-82', 'LK-9', 'LK-91', 'LK-92', 'LR-BG', 'LR-BM', 'LR-CM', 'LR-GB', 'LR-GG', 'LR-GK', 'LR-LO', 'LR-MG', 'LR-MO', 'LR-MY', 'LR-NI', 'LR-RI', 'LR-SI', 'LS-A', 'LS-B', 'LS-C', 'LS-D', 'LS-E', 'LS-F', 'LS-G', 'LS-H', 'LS-J', 'LS-K', 'LT-AL', 'LT-KL', 'LT-KU', 'LT-MR', 'LT-PN', 'LT-SA', 'LT-TA', 'LT-TE', 'LT-UT', 'LT-VL', 'LU-D', 'LU-G', 'LU-L', 'LV-AI', 'LV-AL', 'LV-BL', 'LV-BU', 'LV-CE', 'LV-DA', 'LV-DGV', 'LV-DO', 'LV-GU', 'LV-JEL', 'LV-JK', 'LV-JL', 'LV-JUR', 'LV-KR', 'LV-KU', 'LV-LE', 'LV-LM', 'LV-LPX', 'LV-LU', 'LV-MA', 'LV-OG', 'LV-PR', 'LV-RE', 'LV-REZ', 'LV-RI', 'LV-RIX', 'LV-SA', 'LV-TA', 'LV-TU', 'LV-VE', 'LV-VEN', 'LV-VK', 'LV-VM', 'LY-BA', 'LY-BU', 'LY-FA', 'LY-JA', 'LY-JG', 'LY-JU', 'LY-MI', 'LY-NA', 'LY-SF', 'LY-TB', 'LY-WA', 'LY-WU', 'LY-ZA', 'MA-01', 'MA-02', 'MA-03', 'MA-04', 'MA-05', 'MA-06', 'MA-07', 'MA-08', 'MA-09', 'MA-10', 'MA-11', 'MA-12', 'MA-13', 'MA-14', 'MA-15', 'MA-16', 'MA-AGD', 'MA-ASZ', 'MA-AZI', 'MA-BAH', 'MA-BEM', 'MA-BER', 'MA-BES', 'MA-BOD', 'MA-BOM', 'MA-CAS', 'MA-CHE', 'MA-CHI', 'MA-ERR', 'MA-ESI', 'MA-ESM', 'MA-FES', 'MA-FIG', 'MA-GUE', 'MA-HAJ', 'MA-HAO', 'MA-HOC', 'MA-IFR', 'MA-JDI', 'MA-JRA', 'MA-KEN', 'MA-KES', 'MA-KHE', 'MA-KHN', 'MA-KHO', 'MA-LAA', 'MA-LAR', 'MA-MAR', 'MA-MEK', 'MA-MEL', 'MA-NAD', 'MA-OUA', 'MA-OUD', 'MA-OUJ', 'MA-RBA', 'MA-SAF', 'MA-SEF', 'MA-SET', 'MA-SIK', 'MA-TAO', 'MA-TAR', 'MA-TAT', 'MA-TAZ', 'MA-TET', 'MA-TIZ', 'MA-TNG', 'MA-TNT', 'MD-BA', 'MD-CA', 'MD-CH', 'MD-CU', 'MD-ED', 'MD-GA', 'MD-LA', 'MD-OR', 'MD-SN', 'MD-SO', 'MD-TA', 'MD-TI', 'MD-UN', 'MG-A', 'MG-D', 'MG-F', 'MG-M', 'MG-T', 'MG-U', 'MH-ALK', 'MH-ALL', 'MH-ARN', 'MH-AUR', 'MH-EBO', 'MH-ENI', 'MH-JAL', 'MH-KIL', 'MH-KWA', 'MH-L', 'MH-LAE', 'MH-LIB', 'MH-LIK', 'MH-MAJ', 'MH-MAL', 'MH-MEJ', 'MH-MIL', 'MH-NMK', 'MH-NMU', 'MH-RON', 'MH-T', 'MH-UJA', 'MH-UJL', 'MH-UTI', 'MH-WTH', 'MH-WTJ', 'ML-1', 'ML-2', 'ML-3', 'ML-4', 'ML-5', 'ML-6', 'ML-7', 'ML-8', 'ML-BKO', 'MM-01', 'MM-02', 'MM-03', 'MM-04', 'MM-05', 'MM-06', 'MM-07', 'MM-11', 'MM-12', 'MM-13', 'MM-14', 'MM-15', 'MM-16', 'MM-17', 'MN-035', 'MN-037', 'MN-039', 'MN-041', 'MN-043', 'MN-046', 'MN-047', 'MN-049', 'MN-051', 'MN-053', 'MN-055', 'MN-057', 'MN-059', 'MN-061', 'MN-063', 'MN-064', 'MN-065', 'MN-067', 'MN-069', 'MN-071', 'MN-073', 'MN-1', 'MR-01', 'MR-02', 'MR-03', 'MR-04', 'MR-05', 'MR-06', 'MR-07', 'MR-08', 'MR-09', 'MR-10', 'MR-11', 'MR-12', 'MR-NKC', 'MU-AG', 'MU-BL', 'MU-BR', 'MU-CC', 'MU-CU', 'MU-FL', 'MU-GP', 'MU-MO', 'MU-PA', 'MU-PL', 'MU-PU', 'MU-PW', 'MU-QB', 'MU-RO', 'MU-RR', 'MU-SA', 'MU-VP', 'MV-01', 'MV-02', 'MV-03', 'MV-04', 'MV-05', 'MV-07', 'MV-08', 'MV-12', 'MV-13', 'MV-14', 'MV-17', 'MV-20', 'MV-23', 'MV-24', 'MV-25', 'MV-26', 'MV-27', 'MV-28', 'MV-29', 'MV-MLE', 'MW-BA', 'MW-BL', 'MW-C', 'MW-CK', 'MW-CR', 'MW-CT', 'MW-DE', 'MW-DO', 'MW-KR', 'MW-KS', 'MW-LI', 'MW-LK', 'MW-MC', 'MW-MG', 'MW-MH', 'MW-MU', 'MW-MW', 'MW-MZ', 'MW-N', 'MW-NB', 'MW-NI', 'MW-NK', 'MW-NS', 'MW-NU', 'MW-PH', 'MW-RU', 'MW-S', 'MW-SA', 'MW-TH', 'MW-ZO', 'MX-AGU', 'MX-BCN', 'MX-BCS', 'MX-CAM', 'MX-CHH', 'MX-CHP', 'MX-COA', 'MX-COL', 'MX-DIF', 'MX-DUR', 'MX-GRO', 'MX-GUA', 'MX-HID', 'MX-JAL', 'MX-MEX', 'MX-MIC', 'MX-MOR', 'MX-NAY', 'MX-NLE', 'MX-OAX', 'MX-PUE', 'MX-QUE', 'MX-ROO', 'MX-SIN', 'MX-SLP', 'MX-SON', 'MX-TAB', 'MX-TAM', 'MX-TLA', 'MX-VER', 'MX-YUC', 'MX-ZAC', 'MY-A', 'MY-B', 'MY-C', 'MY-D', 'MY-J', 'MY-K', 'MY-L', 'MY-M', 'MY-N', 'MY-P', 'MY-R', 'MY-SA', 'MY-SK', 'MY-T', 'MY-W', 'MZ-A', 'MZ-B', 'MZ-G', 'MZ-I', 'MZ-L', 'MZ-MPM', 'MZ-N', 'MZ-P', 'MZ-Q', 'MZ-S', 'MZ-T', 'NA-CA', 'NA-ER', 'NA-HA', 'NA-KA', 'NA-KH', 'NA-KU', 'NA-OD', 'NA-OH', 'NA-OK', 'NA-ON', 'NA-OS', 'NA-OT', 'NA-OW', 'NE-1', 'NE-2', 'NE-3', 'NE-4', 'NE-5', 'NE-6', 'NE-7', 'NE-8', 'NG-AB', 'NG-AD', 'NG-AK', 'NG-AN', 'NG-BA', 'NG-BE', 'NG-BO', 'NG-BY', 'NG-CR', 'NG-DE', 'NG-EB', 'NG-ED', 'NG-EK', 'NG-EN', 'NG-FC', 'NG-GO', 'NG-IM', 'NG-JI', 'NG-KD', 'NG-KE', 'NG-KN', 'NG-KO', 'NG-KT', 'NG-KW', 'NG-LA', 'NG-NA', 'NG-NI', 'NG-OG', 'NG-ON', 'NG-OS', 'NG-OY', 'NG-PL', 'NG-RI', 'NG-SO', 'NG-TA', 'NG-YO', 'NG-ZA', 'NI-AN', 'NI-AS', 'NI-BO', 'NI-CA', 'NI-CI', 'NI-CO', 'NI-ES', 'NI-GR', 'NI-JI', 'NI-LE', 'NI-MD', 'NI-MN', 'NI-MS', 'NI-MT', 'NI-NS', 'NI-RI', 'NI-SJ', 'NL-DR', 'NL-FL', 'NL-FR', 'NL-GE', 'NL-GR', 'NL-LI', 'NL-NB', 'NL-NH', 'NL-OV', 'NL-UT', 'NL-ZE', 'NL-ZH', 'NO-01', 'NO-02', 'NO-03', 'NO-04', 'NO-05', 'NO-06', 'NO-07', 'NO-08', 'NO-09', 'NO-10', 'NO-11', 'NO-12', 'NO-14', 'NO-15', 'NO-16', 'NO-17', 'NO-18', 'NO-19', 'NO-20', 'NO-21', 'NO-22', 'NP-1', 'NP-2', 'NP-3', 'NP-4', 'NP-5', 'NP-BA', 'NP-BH', 'NP-DH', 'NP-GA', 'NP-JA', 'NP-KA', 'NP-KO', 'NP-LU', 'NP-MA', 'NP-ME', 'NP-NA', 'NP-RA', 'NP-SA', 'NP-SE', 'NZ-AUK', 'NZ-BOP', 'NZ-CAN', 'NZ-GIS', 'NZ-HKB', 'NZ-MBH', 'NZ-MWT', 'NZ-N', 'NZ-NSN', 'NZ-NTL', 'NZ-OTA', 'NZ-S', 'NZ-STL', 'NZ-TAS', 'NZ-TKI', 'NZ-WGN', 'NZ-WKO', 'NZ-WTC', 'OM-BA', 'OM-DA', 'OM-JA', 'OM-MA', 'OM-MU', 'OM-SH', 'OM-WU', 'OM-ZA', 'PA-0', 'PA-1', 'PA-2', 'PA-3', 'PA-4', 'PA-5', 'PA-6', 'PA-7', 'PA-8', 'PA-9', 'PE-AMA', 'PE-ANC', 'PE-APU', 'PE-ARE', 'PE-AYA', 'PE-CAJ', 'PE-CAL', 'PE-CUS', 'PE-HUC', 'PE-HUV', 'PE-ICA', 'PE-JUN', 'PE-LAL', 'PE-LAM', 'PE-LIM', 'PE-LOR', 'PE-MDD', 'PE-MOQ', 'PE-PAS', 'PE-PIU', 'PE-PUN', 'PE-SAM', 'PE-TAC', 'PE-TUM', 'PE-UCA', 'PG-CPK', 'PG-CPM', 'PG-EBR', 'PG-EHG', 'PG-EPW', 'PG-ESW', 'PG-GPK', 'PG-MBA', 'PG-MPL', 'PG-MPM', 'PG-MRL', 'PG-NCD', 'PG-NIK', 'PG-NPP', 'PG-NSA', 'PG-SAN', 'PG-SHM', 'PG-WBK', 'PG-WHM', 'PG-WPD', 'PH-00', 'PH-01', 'PH-02', 'PH-03', 'PH-04', 'PH-05', 'PH-06', 'PH-07', 'PH-08', 'PH-09', 'PH-10', 'PH-11', 'PH-12', 'PH-13', 'PH-14', 'PH-15', 'PH-ABR', 'PH-AGN', 'PH-AGS', 'PH-AKL', 'PH-ALB', 'PH-ANT', 'PH-APA', 'PH-AUR', 'PH-BAN', 'PH-BAS', 'PH-BEN', 'PH-BIL', 'PH-BOH', 'PH-BTG', 'PH-BTN', 'PH-BUK', 'PH-BUL', 'PH-CAG', 'PH-CAM', 'PH-CAN', 'PH-CAP', 'PH-CAS', 'PH-CAT', 'PH-CAV', 'PH-CEB', 'PH-COM', 'PH-DAO', 'PH-DAS', 'PH-DAV', 'PH-EAS', 'PH-GUI', 'PH-IFU', 'PH-ILI', 'PH-ILN', 'PH-ILS', 'PH-ISA', 'PH-KAL', 'PH-LAG', 'PH-LAN', 'PH-LAS', 'PH-LEY', 'PH-LUN', 'PH-MAD', 'PH-MAG', 'PH-MAS', 'PH-MDC', 'PH-MDR', 'PH-MOU', 'PH-MSC', 'PH-MSR', 'PH-NCO', 'PH-NEC', 'PH-NER', 'PH-NSA', 'PH-NUE', 'PH-NUV', 'PH-PAM', 'PH-PAN', 'PH-PLW', 'PH-QUE', 'PH-QUI', 'PH-RIZ', 'PH-ROM', 'PH-SAR', 'PH-SCO', 'PH-SIG', 'PH-SLE', 'PH-SLU', 'PH-SOR', 'PH-SUK', 'PH-SUN', 'PH-SUR', 'PH-TAR', 'PH-TAW', 'PH-WSA', 'PH-ZAN', 'PH-ZAS', 'PH-ZMB', 'PH-ZSI', 'PK-BA', 'PK-IS', 'PK-JK', 'PK-NA', 'PK-NW', 'PK-PB', 'PK-SD', 'PK-TA', 'PL-DS', 'PL-KP', 'PL-LB', 'PL-LD', 'PL-LU', 'PL-MA', 'PL-MZ', 'PL-OP', 'PL-PD', 'PL-PK', 'PL-PM', 'PL-SK', 'PL-SL', 'PL-WN', 'PL-WP', 'PL-ZP', 'PT-01', 'PT-02', 'PT-03', 'PT-04', 'PT-05', 'PT-06', 'PT-07', 'PT-08', 'PT-09', 'PT-10', 'PT-11', 'PT-12', 'PT-13', 'PT-14', 'PT-15', 'PT-16', 'PT-17', 'PT-18', 'PT-20', 'PT-30', 'PY-1', 'PY-10', 'PY-11', 'PY-12', 'PY-13', 'PY-14', 'PY-15', 'PY-16', 'PY-19', 'PY-2', 'PY-3', 'PY-4', 'PY-5', 'PY-6', 'PY-7', 'PY-8', 'PY-9', 'PY-ASU', 'QA-DA', 'QA-GH', 'QA-JB', 'QA-JU', 'QA-KH', 'QA-MS', 'QA-RA', 'QA-US', 'QA-WA', 'RO-AB', 'RO-AG', 'RO-AR', 'RO-B', 'RO-BC', 'RO-BH', 'RO-BN', 'RO-BR', 'RO-BT', 'RO-BV', 'RO-BZ', 'RO-CJ', 'RO-CL', 'RO-CS', 'RO-CT', 'RO-CV', 'RO-DB', 'RO-DJ', 'RO-GJ', 'RO-GL', 'RO-GR', 'RO-HD', 'RO-HR', 'RO-IF', 'RO-IL', 'RO-IS', 'RO-MH', 'RO-MM', 'RO-MS', 'RO-NT', 'RO-OT', 'RO-PH', 'RO-SB', 'RO-SJ', 'RO-SM', 'RO-SV', 'RO-TL', 'RO-TM', 'RO-TR', 'RO-VL', 'RO-VN', 'RO-VS', 'RU-AD', 'RU-AGB', 'RU-AL', 'RU-ALT', 'RU-AMU', 'RU-ARK', 'RU-AST', 'RU-BA', 'RU-BEL', 'RU-BRY', 'RU-BU', 'RU-CE', 'RU-CHE', 'RU-CHI', 'RU-CHU', 'RU-CU', 'RU-DA', 'RU-DU', 'RU-EVE', 'RU-IN', 'RU-IRK', 'RU-IVA', 'RU-KAM', 'RU-KB', 'RU-KC', 'RU-KDA', 'RU-KEM', 'RU-KGD', 'RU-KGN', 'RU-KHA', 'RU-KHM', 'RU-KIR', 'RU-KK', 'RU-KL', 'RU-KLU', 'RU-KO', 'RU-KOP', 'RU-KOR', 'RU-KOS', 'RU-KR', 'RU-KRS', 'RU-KYA', 'RU-LEN', 'RU-LIP', 'RU-MAG', 'RU-ME', 'RU-MO', 'RU-MOS', 'RU-MOW', 'RU-MUR', 'RU-NEN', 'RU-NGR', 'RU-NIZ', 'RU-NVS', 'RU-OMS', 'RU-ORE', 'RU-ORL', 'RU-PER', 'RU-PNZ', 'RU-PRI', 'RU-PSK', 'RU-ROS', 'RU-RYA', 'RU-SA', 'RU-SAK', 'RU-SAM', 'RU-SAR', 'RU-SE', 'RU-SMO', 'RU-SPE', 'RU-STA', 'RU-SVE', 'RU-TA', 'RU-TAM', 'RU-TAY', 'RU-TOM', 'RU-TUL', 'RU-TVE', 'RU-TY', 'RU-TYU', 'RU-ULY', 'RU-UOB', 'RU-VGG', 'RU-VLA', 'RU-VLG', 'RU-VOR', 'RU-YAN', 'RU-YAR', 'RU-YEV', 'RW-B', 'RW-C', 'RW-D', 'RW-E', 'RW-F', 'RW-G', 'RW-H', 'RW-I', 'RW-J', 'RW-K', 'RW-L', 'RW-M', 'SA-01', 'SA-02', 'SA-03', 'SA-04', 'SA-05', 'SA-06', 'SA-07', 'SA-08', 'SA-09', 'SA-10', 'SA-11', 'SA-12', 'SA-14', 'SB-CE', 'SB-CT', 'SB-GU', 'SB-IS', 'SB-MK', 'SB-ML', 'SB-TE', 'SB-WE', 'SD-01', 'SD-02', 'SD-03', 'SD-04', 'SD-05', 'SD-06', 'SD-07', 'SD-08', 'SD-09', 'SD-10', 'SD-11', 'SD-12', 'SD-13', 'SD-14', 'SD-15', 'SD-16', 'SD-17', 'SD-18', 'SD-19', 'SD-20', 'SD-21', 'SD-22', 'SD-23', 'SD-24', 'SD-25', 'SD-26', 'SE-AB', 'SE-AC', 'SE-BD', 'SE-C', 'SE-D', 'SE-E', 'SE-F', 'SE-G', 'SE-H', 'SE-I', 'SE-K', 'SE-M', 'SE-N', 'SE-O', 'SE-S', 'SE-T', 'SE-U', 'SE-W', 'SE-X', 'SE-Y', 'SE-Z', 'SH-AC', 'SH-SH', 'SH-TA', 'SI-01', 'SI-02', 'SI-03', 'SI-04', 'SI-05', 'SI-06', 'SI-07', 'SI-08', 'SI-09', 'SI-10', 'SI-11', 'SI-12', 'SK-BC', 'SK-BL', 'SK-KI', 'SK-NI', 'SK-PV', 'SK-TA', 'SK-TC', 'SK-ZI', 'SL-E', 'SL-N', 'SL-S', 'SL-W', 'SN-DB', 'SN-DK', 'SN-FK', 'SN-KD', 'SN-KL', 'SN-LG', 'SN-SL', 'SN-TC', 'SN-TH', 'SN-ZG', 'SO-AW', 'SO-BK', 'SO-BN', 'SO-BR', 'SO-BY', 'SO-GA', 'SO-GE', 'SO-HI', 'SO-JD', 'SO-JH', 'SO-MU', 'SO-NU', 'SO-SA', 'SO-SD', 'SO-SH', 'SO-SO', 'SO-TO', 'SO-WO', 'SR-BR', 'SR-CM', 'SR-CR', 'SR-MA', 'SR-NI', 'SR-PM', 'SR-PR', 'SR-SA', 'SR-SI', 'SR-WA', 'ST-P', 'ST-S', 'SV-AH', 'SV-CA', 'SV-CH', 'SV-CU', 'SV-LI', 'SV-MO', 'SV-PA', 'SV-SA', 'SV-SM', 'SV-SO', 'SV-SS', 'SV-SV', 'SV-UN', 'SV-US', 'SY-DI', 'SY-DR', 'SY-DY', 'SY-HA', 'SY-HI', 'SY-HL', 'SY-HM', 'SY-ID', 'SY-LA', 'SY-QU', 'SY-RA', 'SY-RD', 'SY-SU', 'SY-TA', 'SZ-HH', 'SZ-LU', 'SZ-MA', 'SZ-SH', 'TD-BA', 'TD-BET', 'TD-BI', 'TD-CB', 'TD-GR', 'TD-KA', 'TD-LC', 'TD-LO', 'TD-LR', 'TD-MC', 'TD-MK', 'TD-OD', 'TD-SA', 'TD-TA', 'TG-C', 'TG-K', 'TG-M', 'TG-P', 'TG-S', 'TH-10', 'TH-11', 'TH-12', 'TH-13', 'TH-14', 'TH-15', 'TH-16', 'TH-17', 'TH-18', 'TH-19', 'TH-20', 'TH-21', 'TH-22', 'TH-23', 'TH-24', 'TH-25', 'TH-26', 'TH-27', 'TH-30', 'TH-31', 'TH-32', 'TH-33', 'TH-34', 'TH-35', 'TH-36', 'TH-37', 'TH-39', 'TH-40', 'TH-41', 'TH-42', 'TH-43', 'TH-44', 'TH-45', 'TH-46', 'TH-47', 'TH-48', 'TH-49', 'TH-50', 'TH-51', 'TH-52', 'TH-53', 'TH-54', 'TH-55', 'TH-56', 'TH-57', 'TH-58', 'TH-60', 'TH-61', 'TH-62', 'TH-63', 'TH-64', 'TH-65', 'TH-66', 'TH-67', 'TH-70', 'TH-71', 'TH-72', 'TH-73', 'TH-74', 'TH-75', 'TH-76', 'TH-77', 'TH-80', 'TH-81', 'TH-82', 'TH-83', 'TH-84', 'TH-85', 'TH-86', 'TH-90', 'TH-91', 'TH-92', 'TH-93', 'TH-94', 'TH-95', 'TH-96', 'TH-S', 'TJ-GB', 'TJ-KT', 'TJ-SU', 'TL-AL', 'TL-AN', 'TL-BA', 'TL-BO', 'TL-CO', 'TL-DI', 'TL-ER', 'TL-LA', 'TL-LI', 'TL-MF', 'TL-MT', 'TL-OE', 'TL-VI', 'TM-A', 'TM-B', 'TM-D', 'TM-L', 'TM-M', 'TN-11', 'TN-12', 'TN-13', 'TN-21', 'TN-22', 'TN-23', 'TN-31', 'TN-32', 'TN-33', 'TN-34', 'TN-41', 'TN-42', 'TN-43', 'TN-51', 'TN-52', 'TN-53', 'TN-61', 'TN-71', 'TN-72', 'TN-73', 'TN-81', 'TN-82', 'TN-83', 'TR-01', 'TR-02', 'TR-03', 'TR-04', 'TR-05', 'TR-06', 'TR-07', 'TR-08', 'TR-09', 'TR-10', 'TR-11', 'TR-12', 'TR-13', 'TR-14', 'TR-15', 'TR-16', 'TR-17', 'TR-18', 'TR-19', 'TR-20', 'TR-21', 'TR-22', 'TR-23', 'TR-24', 'TR-25', 'TR-26', 'TR-27', 'TR-28', 'TR-29', 'TR-30', 'TR-31', 'TR-32', 'TR-33', 'TR-34', 'TR-35', 'TR-36', 'TR-37', 'TR-38', 'TR-39', 'TR-40', 'TR-41', 'TR-42', 'TR-43', 'TR-44', 'TR-45', 'TR-46', 'TR-47', 'TR-48', 'TR-49', 'TR-50', 'TR-51', 'TR-52', 'TR-53', 'TR-54', 'TR-55', 'TR-56', 'TR-57', 'TR-58', 'TR-59', 'TR-60', 'TR-61', 'TR-62', 'TR-63', 'TR-64', 'TR-65', 'TR-66', 'TR-67', 'TR-68', 'TR-69', 'TR-70', 'TR-71', 'TR-72', 'TR-73', 'TR-74', 'TR-75', 'TR-76', 'TR-77', 'TR-78', 'TR-79', 'TR-80', 'TR-81', 'TT-ARI', 'TT-CHA', 'TT-CTT', 'TT-DMN', 'TT-ETO', 'TT-PED', 'TT-POS', 'TT-PRT', 'TT-PTF', 'TT-RCM', 'TT-SFO', 'TT-SGE', 'TT-SIP', 'TT-SJL', 'TT-TUP', 'TT-WTO', 'TW-CHA', 'TW-CYQ', 'TW-HSQ', 'TW-HUA', 'TW-ILA', 'TW-KEE', 'TW-KHQ', 'TW-MIA', 'TW-NAN', 'TW-PEN', 'TW-PIF', 'TW-TAO', 'TW-TNQ', 'TW-TPQ', 'TW-TTT', 'TW-TXQ', 'TW-YUN', 'TZ-01', 'TZ-02', 'TZ-03', 'TZ-04', 'TZ-05', 'TZ-06', 'TZ-07', 'TZ-08', 'TZ-09', 'TZ-10', 'TZ-11', 'TZ-12', 'TZ-13', 'TZ-14', 'TZ-15', 'TZ-16', 'TZ-17', 'TZ-18', 'TZ-19', 'TZ-20', 'TZ-21', 'TZ-22', 'TZ-23', 'TZ-24', 'TZ-25', 'UA-05', 'UA-07', 'UA-09', 'UA-12', 'UA-14', 'UA-18', 'UA-21', 'UA-23', 'UA-26', 'UA-30', 'UA-32', 'UA-35', 'UA-40', 'UA-43', 'UA-46', 'UA-48', 'UA-51', 'UA-53', 'UA-56', 'UA-59', 'UA-61', 'UA-63', 'UA-65', 'UA-68', 'UA-71', 'UA-74', 'UA-77', 'UG-AJM', 'UG-APA', 'UG-ARU', 'UG-BUA', 'UG-BUG', 'UG-BUN', 'UG-BUS', 'UG-C', 'UG-E', 'UG-GUL', 'UG-HOI', 'UG-IGA', 'UG-JIN', 'UG-KAP', 'UG-KAS', 'UG-KAT', 'UG-KBL', 'UG-KBR', 'UG-KIB', 'UG-KIS', 'UG-KIT', 'UG-KLA', 'UG-KLE', 'UG-KLG', 'UG-KLI', 'UG-KOT', 'UG-KUM', 'UG-LIR', 'UG-LUW', 'UG-MBL', 'UG-MBR', 'UG-MOR', 'UG-MOY', 'UG-MPI', 'UG-MSI', 'UG-MSK', 'UG-MUB', 'UG-MUK', 'UG-N', 'UG-NAK', 'UG-NEB', 'UG-NTU', 'UG-PAL', 'UG-RAK', 'UG-RUK', 'UG-SEM', 'UG-SOR', 'UG-TOR', 'UG-W', 'UM-67', 'UM-71', 'UM-76', 'UM-79', 'UM-81', 'UM-84', 'UM-86', 'UM-89', 'UM-95', 'US-AK', 'US-AL', 'US-AR', 'US-AS', 'US-AZ', 'US-CA', 'US-CO', 'US-CT', 'US-DC', 'US-DE', 'US-FL', 'US-GA', 'US-GU', 'US-HI', 'US-IA', 'US-ID', 'US-IL', 'US-IN', 'US-KS', 'US-KY', 'US-LA', 'US-MA', 'US-MD', 'US-ME', 'US-MI', 'US-MN', 'US-MO', 'US-MP', 'US-MS', 'US-MT', 'US-NC', 'US-ND', 'US-NE', 'US-NH', 'US-NJ', 'US-NM', 'US-NV', 'US-NY', 'US-OH', 'US-OK', 'US-OR', 'US-PA', 'US-PR', 'US-RI', 'US-SC', 'US-SD', 'US-TN', 'US-TX', 'US-UM', 'US-UT', 'US-VA', 'US-VI', 'US-VT', 'US-WA', 'US-WI', 'US-WV', 'US-WY', 'UY-AR', 'UY-CA', 'UY-CL', 'UY-CO', 'UY-DU', 'UY-FD', 'UY-FS', 'UY-LA', 'UY-MA', 'UY-MO', 'UY-PA', 'UY-RN', 'UY-RO', 'UY-RV', 'UY-SA', 'UY-SJ', 'UY-SO', 'UY-TA', 'UY-TT', 'UZ-AN', 'UZ-BU', 'UZ-FA', 'UZ-JI', 'UZ-NG', 'UZ-NW', 'UZ-QA', 'UZ-QR', 'UZ-SA', 'UZ-SI', 'UZ-SU', 'UZ-TK', 'UZ-TO', 'UZ-XO', 'VE-A', 'VE-B', 'VE-C', 'VE-D', 'VE-E', 'VE-F', 'VE-G', 'VE-H', 'VE-I', 'VE-J', 'VE-K', 'VE-L', 'VE-M', 'VE-N', 'VE-O', 'VE-P', 'VE-R', 'VE-S', 'VE-T', 'VE-U', 'VE-V', 'VE-W', 'VE-X', 'VE-Y', 'VE-Z', 'VN-01', 'VN-02', 'VN-03', 'VN-04', 'VN-05', 'VN-06', 'VN-07', 'VN-09', 'VN-13', 'VN-14', 'VN-15', 'VN-18', 'VN-20', 'VN-21', 'VN-22', 'VN-23', 'VN-24', 'VN-25', 'VN-26', 'VN-27', 'VN-28', 'VN-29', 'VN-30', 'VN-31', 'VN-32', 'VN-33', 'VN-34', 'VN-35', 'VN-36', 'VN-37', 'VN-39', 'VN-40', 'VN-41', 'VN-43', 'VN-44', 'VN-45', 'VN-46', 'VN-47', 'VN-48', 'VN-49', 'VN-50', 'VN-51', 'VN-52', 'VN-53', 'VN-54', 'VN-55', 'VN-56', 'VN-57', 'VN-58', 'VN-59', 'VN-60', 'VN-61', 'VN-62', 'VN-63', 'VN-64', 'VN-65', 'VN-66', 'VN-67', 'VN-68', 'VN-69', 'VN-70', 'VU-MAP', 'VU-PAM', 'VU-SAM', 'VU-SEE', 'VU-TAE', 'VU-TOB', 'WS-AA', 'WS-AL', 'WS-AT', 'WS-FA', 'WS-GE', 'WS-GI', 'WS-PA', 'WS-SA', 'WS-TU', 'WS-VF', 'WS-VS', 'YE-AB', 'YE-AD', 'YE-AM', 'YE-BA', 'YE-DA', 'YE-DH', 'YE-HD', 'YE-HJ', 'YE-HU', 'YE-IB', 'YE-JA', 'YE-LA', 'YE-MA', 'YE-MR', 'YE-MW', 'YE-SD', 'YE-SH', 'YE-SN', 'YE-TA', 'YU-CG', 'YU-KM', 'YU-SR', 'YU-VO', 'ZA-EC', 'ZA-FS', 'ZA-GT', 'ZA-MP', 'ZA-NC', 'ZA-NL', 'ZA-NP', 'ZA-NW', 'ZA-WC', 'ZM-01', 'ZM-02', 'ZM-03', 'ZM-04', 'ZM-05', 'ZM-06', 'ZM-07', 'ZM-08', 'ZM-09', 'ZW-BU', 'ZW-HA', 'ZW-MA', 'ZW-MC', 'ZW-ME', 'ZW-MI', 'ZW-MN', 'ZW-MS', 'ZW-MV', 'ZW-MW', name='subdivision'), nullable=False),
                    sa.Column('city', sa.Unicode(length=32), nullable=False),
    sa.Column('city_confidence', sa.SmallInteger(), nullable=False),
    sa.Column('isp', sa.Unicode(length=32), nullable=False),
    sa.Column('organization', sa.Unicode(length=32), nullable=True),
    sa.Column('organization_type', sa.Unicode(length=32), nullable=True),
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action_with_one_device.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Rate table
    op.create_table('rate',
                    sa.Column('rating', sa.Float(decimal_return_scale=2), nullable=True, comment='The rating for the content.'),
                    sa.Column('version', teal.db.StrictVersionType(), nullable=True, comment='The version of the software.'),
                    sa.Column('appearance', sa.Float(decimal_return_scale=2), nullable=True, comment='Subjective value representing aesthetic aspects.'),
                    sa.Column('functionality', sa.Float(decimal_return_scale=2), nullable=True, comment='Subjective value representing usage aspects.'),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action_with_one_device.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Snapshot table
    op.create_table('snapshot',
                    sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('version', teal.db.StrictVersionType(length=32), nullable=False),
                    sa.Column('software', sa.Enum('Workbench', 'WorkbenchAndroid', 'AndroidApp', 'Web', 'DesktopApp', name='snapshotsoftware'), nullable=False),
                    sa.Column('elapsed', sa.Interval(), nullable=True, comment='For Snapshots made with Workbench, the total amount \n    of time it took to complete.\n    '),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action_with_one_device.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('uuid'),
                    schema=f'{get_inv()}'
                    )

    # Test table
    op.create_table('test',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action_with_one_device.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # BenchmarkDataStorage table
    op.create_table('benchmark_data_storage',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('read_speed', sa.Float(decimal_return_scale=2), nullable=False),
                    sa.Column('write_speed', sa.Float(decimal_return_scale=2), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.benchmark.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # BenchmarkWithRate table
    op.create_table('benchmark_with_rate',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('rate', sa.Float(), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.benchmark.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # MeasureBattery table
    op.create_table('measure_battery',
                    sa.Column('size', sa.Integer(), nullable=False, comment='Maximum battery capacity, in mAh.'),
                    sa.Column('voltage', sa.Integer(), nullable=False, comment='The actual voltage of the battery, in mV.'),
                    sa.Column('cycle_count', sa.Integer(), nullable=True, comment='The number of full charges – discharges \n    cycles.\n    '),
                    sa.Column('health', sa.Enum('Cold', 'Dead', 'Good', 'Overheat', 'OverVoltage', 'UnspecifiedValue', name='batteryhealth'), nullable=True, comment='The health of the Battery. \n    Only reported in Android.\n    '),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.test.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Price table
    op.create_table('price',
                    sa.Column('currency', sa.Enum('AFN', 'ARS', 'AWG', 'AUD', 'AZN', 'BSD', 'BBD', 'BDT', 'BYR', 'BZD', 'BMD', 'BOB', 'BAM', 'BWP', 'BGN', 'BRL', 'BND', 'KHR', 'CAD', 'KYD', 'CLP', 'CNY', 'COP', 'CRC', 'HRK', 'CUP', 'CZK', 'DKK', 'DOP', 'XCD', 'EGP', 'SVC', 'EEK', 'EUR', 'FKP', 'FJD', 'GHC', 'GIP', 'GTQ', 'GGP', 'GYD', 'HNL', 'HKD', 'HUF', 'ISK', 'INR', 'IDR', 'IRR', 'IMP', 'ILS', 'JMD', 'JPY', 'JEP', 'KZT', 'KPW', 'KRW', 'KGS', 'LAK', 'LVL', 'LBP', 'LRD', 'LTL', 'MKD', 'MYR', 'MUR', 'MXN', 'MNT', 'MZN', 'NAD', 'NPR', 'ANG', 'NZD', 'NIO', 'NGN', 'NOK', 'OMR', 'PKR', 'PAB', 'PYG', 'PEN', 'PHP', 'PLN', 'QAR', 'RON', 'RUB', 'SHP', 'SAR', 'RSD', 'SCR', 'SGD', 'SBD', 'SOS', 'ZAR', 'LKR', 'SEK', 'CHF', 'SRD', 'SYP', 'TWD', 'THB', 'TTD', 'TRY', 'TRL', 'TVD', 'UAH', 'GBP', 'USD', 'UYU', 'UZS', 'VEF', 'VND', 'YER', 'ZWD', name='currency'), nullable=False, comment='The currency of this price as for ISO 4217.'),
                    sa.Column('price', sa.Numeric(precision=19, scale=4), nullable=False, comment='The value.'),
                    sa.Column('software', sa.Enum('Ereuse', name='pricesoftware'), nullable=True, comment='The software used to compute this price,\n    if the price was computed automatically. This field is None\n    if the price has been manually set.\n    '),
                    sa.Column('version', teal.db.StrictVersionType(), nullable=True, comment='The version of the software, or None.'),
                    sa.Column('rating_id', postgresql.UUID(as_uuid=True), nullable=True, comment='The Rate used to auto-compute\n    this price, if it has not been set manually.\n    '),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action_with_one_device.id'], ),
                    sa.ForeignKeyConstraint(['rating_id'], [f'{get_inv()}.rate.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # ProofDataWipe table
    op.create_table('proof_data_wipe',
                    sa.Column('date', sa.DateTime(), nullable=False),
                    sa.Column('result', sa.Boolean(), nullable=False, comment='Identifies proof datawipe as a result.'),
                    sa.Column('proof_author_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('erasure_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['erasure_id'], [f'{get_inv()}.erase_basic.id'], ),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.proof.id'], ),
                    sa.ForeignKeyConstraint(['proof_author_id'], ['common.user.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # PRoofFuntion
    op.create_table('proof_function',
                    sa.Column('disk_usage', sa.Integer(), nullable=True),
                    sa.Column('proof_author_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('rate_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.proof.id'], ),
                    sa.ForeignKeyConstraint(['proof_author_id'], ['common.user.id'], ),
                    sa.ForeignKeyConstraint(['rate_id'], [f'{get_inv()}.rate.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # RateComputer table
    op.create_table('rate_computer',
                    sa.Column('processor', sa.Float(decimal_return_scale=2), nullable=True, comment='The rate of the Processor.'),
                    sa.Column('ram', sa.Float(decimal_return_scale=2), nullable=True, comment='The rate of the RAM.'),
                    sa.Column('data_storage', sa.Float(decimal_return_scale=2), nullable=True, comment="'Data storage rate, like HHD, SSD.'"),
                    sa.Column('graphic_card', sa.Float(decimal_return_scale=2), nullable=True, comment='Graphic card rate.'),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.rate.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # SnapshotRequest table
    op.create_table('snapshot_request',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('request', sa.JSON(), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.snapshot.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Step table
    op.create_table('step',
                    sa.Column('erasure_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('type', sa.Unicode(length=32), nullable=False),
                    sa.Column('num', sa.SmallInteger(), nullable=False),
                    sa.Column('severity', teal.db.IntEnum(Severity), nullable=False),
                    sa.Column('start_time', sa.TIMESTAMP(timezone=True), nullable=False, comment='When the action starts. For some actions like\n    reservations the time when they are available, for others like renting\n    when the renting starts.\n    '),
                    sa.Column('end_time', sa.TIMESTAMP(timezone=True), nullable=False, comment='When the action ends. For some actions like reservations\n    the time when they expire, for others like renting\n    the time the end rents. For punctual actions it is the time \n    they are performed; it differs with ``created`` in which\n    created is the where the system received the action.\n    '),
                    sa.ForeignKeyConstraint(['erasure_id'], [f'{get_inv()}.erase_basic.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('erasure_id', 'num'),
                    schema=f'{get_inv()}'
                    )

    op.create_table('stress_test',
                    sa.Column('elapsed', sa.Interval(), nullable=False),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.test.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    op.create_table('test_audio',
                    sa.Column('speaker', sa.Boolean(), nullable=True, comment='Whether the speaker works as expected.'),
                    sa.Column('microphone', sa.Boolean(), nullable=True, comment='Whether the microphone works as expected.'),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.test.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    op.create_table('test_bios',
                    sa.Column('beeps_power_on', sa.Boolean(), nullable=True, comment='Whether there are no beeps or error\n    codes when booting up.\n    \n    Reference: R2 provision 6 page 23.\n    '),
                    sa.Column('access_range', sa.Enum('A', 'B', 'C', 'D', 'E', name='biosaccessrange'), nullable=True, comment='Difficulty to modify the boot menu.\n     \n    This is used as an usability measure for accessing and modifying\n    a bios, specially as something as important as modifying the boot\n    menu.\n    '),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.test.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    op.create_table('test_camera',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.test.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    op.create_table('test_connectivity',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.test.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    op.create_table('test_data_storage',
                    sa.Column('length', sa.Enum('Short', 'Extended', name='testdatastoragelength'), nullable=False),
                    sa.Column('status', sa.Unicode(), nullable=False),
                    sa.Column('lifetime', sa.Interval(), nullable=True),
                    sa.Column('assessment', sa.Boolean(), nullable=True),
                    sa.Column('reallocated_sector_count', sa.SmallInteger(), nullable=True),
                    sa.Column('power_cycle_count', sa.SmallInteger(), nullable=True),
                    sa.Column('reported_uncorrectable_errors', sa.Integer(), nullable=True),
                    sa.Column('command_timeout', sa.Integer(), nullable=True),
                    sa.Column('current_pending_sector_count', sa.SmallInteger(), nullable=True),
                    sa.Column('offline_uncorrectable', sa.SmallInteger(), nullable=True),
                    sa.Column('remaining_lifetime_percentage', sa.SmallInteger(), nullable=True),
                    sa.Column('elapsed', sa.Interval(), nullable=False),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.test.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # TestDisplayHinge table
    op.create_table('test_display_hinge',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.test.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # TestKeyboard table
    op.create_table('test_keyboard',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.test.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # TestPowerAdapter table
    op.create_table('test_power_adapter',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.test.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # TestTrackpad table
    op.create_table('test_trackpad',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.test.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # VisualTest table
    op.create_table('visual_test',
                    sa.Column('appearance_range', sa.Enum('Z', 'A', 'B', 'C', 'D', 'E', name='appearancerange'), nullable=True, comment='Grades the imperfections that aesthetically affect the device, but not its usage.'),
                    sa.Column('functionality_range', sa.Enum('A', 'B', 'C', 'D', name='functionalityrange'), nullable=True, comment='Grades the defects of a device that affect its usage.'),
                    sa.Column('labelling', sa.Boolean(), nullable=True, comment='Whether there are tags to be removed.'),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.test.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )

    # Trade table
    op.create_table('trade',
                    sa.Column('shipping_date', sa.TIMESTAMP(timezone=True), nullable=True, comment='When are the devices going to be ready \n    for shipping?\n    '),
                    sa.Column('invoice_number', citext.CIText(), nullable=True, comment='The id of the invoice so they can be linked.'),
                    sa.Column('price_id', postgresql.UUID(as_uuid=True), nullable=True, comment='The price set for this trade.            \n    If no price is set it is supposed that the trade was\n    not payed, usual in donations.\n        '),
                    sa.Column('to_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('confirms_id', postgresql.UUID(as_uuid=True), nullable=True, comment='An organize action that this association confirms.                \n    \n    For example, a ``Sell`` or ``Rent``\n    can confirm a ``Reserve`` action.\n    '),
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.ForeignKeyConstraint(['confirms_id'], [f'{get_inv()}.organize.id'], ),
                    sa.ForeignKeyConstraint(['id'], [f'{get_inv()}.action.id'], ),
                    sa.ForeignKeyConstraint(['price_id'], [f'{get_inv()}.price.id'], ),
                    sa.ForeignKeyConstraint(['to_id'], [f'{get_inv()}.agent.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    schema=f'{get_inv()}'
                    )
    # ### end Alembic commands ###


def downgrade():
    # Drop table, indexes in inventory schema
    op.drop_table('trade', schema=f'{get_inv()}')

    op.drop_table('visual_test', schema=f'{get_inv()}')

    op.drop_table('test_trackpad', schema=f'{get_inv()}')

    op.drop_table('test_power_adapter', schema=f'{get_inv()}')

    op.drop_table('test_keyboard', schema=f'{get_inv()}')

    op.drop_table('test_display_hinge', schema=f'{get_inv()}')

    op.drop_table('test_data_storage', schema=f'{get_inv()}')

    op.drop_table('test_connectivity', schema=f'{get_inv()}')

    op.drop_table('test_camera', schema=f'{get_inv()}')

    op.drop_table('test_bios', schema=f'{get_inv()}')

    op.drop_table('test_audio', schema=f'{get_inv()}')

    op.drop_table('stress_test', schema=f'{get_inv()}')

    op.drop_table('step', schema=f'{get_inv()}')

    op.drop_table('snapshot_request', schema=f'{get_inv()}')

    op.drop_table('rate_computer', schema=f'{get_inv()}')

    op.drop_table('proof_function', schema=f'{get_inv()}')

    op.drop_table('proof_data_wipe', schema=f'{get_inv()}')

    op.drop_table('price', schema=f'{get_inv()}')

    op.drop_table('measure_battery', schema=f'{get_inv()}')

    op.drop_table('benchmark_with_rate', schema=f'{get_inv()}')

    op.drop_table('benchmark_data_storage', schema=f'{get_inv()}')

    op.drop_table('test', schema=f'{get_inv()}')

    op.drop_constraint("snapshot_actions", "action", type_="foreignkey", schema=f'{get_inv()}')
    op.drop_table('snapshot', schema=f'{get_inv()}')

    op.drop_table('rate', schema=f'{get_inv()}')

    op.drop_table('live', schema=f'{get_inv()}')

    op.drop_table('install', schema=f'{get_inv()}')

    op.drop_table('erase_basic', schema=f'{get_inv()}')

    op.drop_table('benchmark', schema=f'{get_inv()}')

    op.drop_table('sound_card', schema=f'{get_inv()}')

    op.drop_table('receive', schema=f'{get_inv()}')

    op.drop_table('ram_module', schema=f'{get_inv()}')

    op.drop_table('processor', schema=f'{get_inv()}')

    op.drop_table('organize', schema=f'{get_inv()}')

    op.drop_table('network_adapter', schema=f'{get_inv()}')

    op.drop_table('motherboard', schema=f'{get_inv()}')

    op.drop_table('migrate', schema=f'{get_inv()}')

    op.drop_index(op.f('ix_membership_updated'), table_name='membership', schema=f'{get_inv()}')
    op.drop_index(op.f('ix_membership_created'), table_name='membership', schema=f'{get_inv()}')
    op.drop_table('membership', schema=f'{get_inv()}')

    op.drop_table('graphic_card', schema=f'{get_inv()}')

    op.drop_table('display', schema=f'{get_inv()}')

    op.drop_table('deallocate', schema=f'{get_inv()}')

    op.drop_table('data_storage', schema=f'{get_inv()}')

    op.drop_table('battery', schema=f'{get_inv()}')

    op.drop_table('allocate', schema=f'{get_inv()}')

    op.drop_index('action_one_device_id_index', table_name='action_with_one_device', schema=f'{get_inv()}')
    op.drop_table('action_with_one_device', schema=f'{get_inv()}')

    op.drop_table('action_device', schema=f'{get_inv()}')

    op.drop_table('action_component', schema=f'{get_inv()}')

    op.drop_index(op.f('ix_tag_updated'), table_name='tag', schema=f'{get_inv()}')
    op.drop_index(op.f('ix_tag_secondary'), table_name='tag', schema=f'{get_inv()}')
    op.drop_index(op.f('ix_tag_created'), table_name='tag', schema=f'{get_inv()}')
    op.drop_index('device_id_index', table_name='tag', schema=f'{get_inv()}')
    op.drop_table('tag', schema=f'{get_inv()}')

    op.drop_table('proof_transfer', schema=f'{get_inv()}')

    op.drop_table('proof_reuse', schema=f'{get_inv()}')

    op.drop_table('proof_recycling', schema=f'{get_inv()}')

    op.drop_index('path_gist', table_name='path', schema=f'{get_inv()}')
    op.drop_index('path_btree', table_name='path', schema=f'{get_inv()}')
    op.drop_index('lot_id_index', table_name='path', schema=f'{get_inv()}')

    op.execute(f"DROP VIEW {get_inv()}.lot_device_descendants")
    op.execute(f"DROP VIEW {get_inv()}.lot_parent")

    op.drop_table('path', schema=f'{get_inv()}')

    op.drop_table('lot_device', schema=f'{get_inv()}')

    op.drop_table('individual', schema=f'{get_inv()}')

    op.drop_index(op.f('ix_deliverynote_updated'), table_name='deliverynote', schema=f'{get_inv()}')
    op.drop_index(op.f('ix_deliverynote_created'), table_name='deliverynote', schema=f'{get_inv()}')
    op.drop_table('deliverynote', schema=f'{get_inv()}')

    op.drop_index('parent_index', table_name='component', schema=f'{get_inv()}')
    op.drop_table('component', schema=f'{get_inv()}')

    op.drop_index('ix_type', table_name='action', schema=f'{get_inv()}')
    op.drop_index('ix_parent_id', table_name='action', schema=f'{get_inv()}')
    op.drop_index('ix_id', table_name='action', schema=f'{get_inv()}')
    op.drop_index(op.f('ix_action_updated'), table_name='action', schema=f'{get_inv()}')
    op.drop_index(op.f('ix_action_created'), table_name='action', schema=f'{get_inv()}')
    op.drop_table('action', schema=f'{get_inv()}')

    op.drop_index(op.f('ix_proof_updated'), table_name='proof', schema=f'{get_inv()}')
    op.drop_index(op.f('ix_proof_created'), table_name='proof', schema=f'{get_inv()}')
    op.drop_table('proof', schema=f'{get_inv()}')

    op.drop_table('printer', schema=f'{get_inv()}')

    op.drop_table('organization', schema=f'{get_inv()}')

    op.drop_table('networking', schema=f'{get_inv()}')

    op.drop_table('monitor', schema=f'{get_inv()}')

    op.drop_table('mobile', schema=f'{get_inv()}')

    op.drop_index(op.f('ix_lot_updated'), table_name='lot', schema=f'{get_inv()}')
    op.drop_index(op.f('ix_lot_created'), table_name='lot', schema=f'{get_inv()}')
    op.drop_table('lot', schema=f'{get_inv()}')

    op.drop_index('tags gist', table_name='device_search', schema=f'{get_inv()}')
    op.drop_index('properties gist', table_name='device_search', schema=f'{get_inv()}')
    op.drop_table('device_search', schema=f'{get_inv()}')

    op.drop_table('computer_accessory', schema=f'{get_inv()}')

    op.drop_table('computer', schema=f'{get_inv()}')

    op.drop_index('type_index', table_name='device', schema=f'{get_inv()}')
    op.drop_index(op.f('ix_device_updated'), table_name='device', schema=f'{get_inv()}')
    op.drop_index(op.f('ix_device_created'), table_name='device', schema=f'{get_inv()}')
    op.drop_index('device_id', table_name='device', schema=f'{get_inv()}')
    op.drop_table('device', schema=f'{get_inv()}')


    op.drop_index(op.f('ix_agent_updated'), table_name='agent', schema=f'{get_inv()}')
    op.drop_index(op.f('ix_agent_created'), table_name='agent', schema=f'{get_inv()}')
    op.drop_index('agent_type', table_name='agent', schema=f'{get_inv()}')
    op.drop_table('agent', schema=f'{get_inv()}')

    # Drop table, indexes in common schema
    op.drop_table('user_inventory', schema='common')

    op.drop_index(op.f('ix_common_user_updated'), table_name='user', schema='common')
    op.drop_index(op.f('ix_common_user_created'), table_name='user', schema='common')
    op.drop_table('user', schema='common')

    op.drop_table('manufacturer', schema='common')

    op.drop_index(op.f('ix_common_inventory_updated'), table_name='inventory', schema='common')
    op.drop_index(op.f('ix_common_inventory_created'), table_name='inventory', schema='common')
    op.drop_index('id_hash', table_name='inventory', schema='common')
    op.drop_table('inventory', schema='common')

    # Drop sequences
    op.execute(f"DROP SEQUENCE {get_inv()}.device_seq;")

    # Drop functions
    op.execute(f"DROP FUNCTION IF EXISTS {get_inv()}.add_edge")
    op.execute(f"DROP FUNCTION IF EXISTS {get_inv()}.delete_edge")

    # Drop Create Common schema
    op.execute("drop schema common")
    op.execute(f"drop schema {get_inv()}")
