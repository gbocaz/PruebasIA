from app.models.device import Device, DeviceGroup, DeviceGroupMember
from app.schemas.ops import DeviceOut


def device_to_out(device: Device) -> DeviceOut:
    groups = [link.group.name for link in device.group_links if link.group]
    return DeviceOut.model_validate(device).model_copy(update={"groups": groups})


def set_device_groups(db, device: Device, group_ids: list[str]) -> None:
    device.group_links.clear()
    for gid in group_ids:
        group = db.get(DeviceGroup, gid)
        if group is None:
            continue
        device.group_links.append(DeviceGroupMember(device=device, group=group))
