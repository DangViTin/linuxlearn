---
chapter: 97
title: BLE Mesh
part: VII — Device cookbook
estimated_pages: 16
status: draft
---

# Chapter 97 — BLE Mesh

> **What:** **Bluetooth Mesh** — a many-to-many networking layer built on BLE advertising, where dozens-to-thousands of nodes relay messages for each other to cover a building. This chapter covers four things: the mesh architecture (elements, models, addresses, publish/subscribe), the **bluez-mesh** stack on Linux, the provisioning flow that adds a node to a network, and a worked lighting-control example with the i.MX6ULL as gateway and provisioner.
> **Why:** BLE point-to-point (Ch 95) reaches one device at ~30 m. BLE Mesh covers an entire building with hundreds of nodes: smart lighting (the dominant use case), building sensors, industrial monitoring. Nodes relay each other's messages to extend coverage. It is the technology behind commercial smart-lighting systems, the kind installed in offices and warehouses. An i.MX6ULL makes a good mesh gateway, bridging mesh traffic to WiFi or the cloud. It can also act as a provisioner, adding new nodes to the network.
> **Focus:** mesh is a publish/subscribe protocol layered on flooded BLE advertisements, with addresses tied to models. A node has *elements*, each with *models* (e.g., a "Generic OnOff Server" model for a light). Messages are *published* to *group addresses*; nodes *subscribed* to that group act on them. "Turn off all kitchen lights" means: publish OnOff=0 to the "kitchen" group. Every light subscribed to "kitchen" responds. Flooding plus relay gives whole-building coverage without any backbone wiring.
> **Tooling.** This chapter uses `bluez` + `bluetooth-meshd` + `mesh-cfgclient`.
> - **Ubuntu-base (target):** `apt install bluez bluez-meshd`
> - **Buildroot:** `BR2_PACKAGE_BLUEZ5_UTILS=y  # (mesh requires the Buildroot experimental option)`
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).

## 97.1  Why mesh, not point-to-point

| | BLE point-to-point (Ch 95) | BLE Mesh |
|---|---|---|
| Topology | star (1 central, N peripherals) | mesh (any-to-any via relays) |
| Range | ~30 m (1 hop) | whole building (multi-hop relay) |
| Nodes | ~7 simultaneous connections | thousands |
| Addressing | per-connection | unicast + group + virtual addresses |
| Model | GATT (connection-oriented) | publish/subscribe (connectionless) |
| Use case | one device ↔ phone | building-scale lighting/sensors |
| Killer app | provisioning, sensor-to-phone | smart lighting |

Mesh sacrifices some point-to-point simplicity. In return you get scale and coverage. A message hops node-to-node. A light in a far room can relay a message it overhears, extending the range far beyond a single radio's reach.

## 97.2  Mesh architecture

```
   Node (a physical device, e.g., a smart light)
    └─ Element (an addressable part; a light might have 1 element)
        └─ Models (the functional units):
            - Generic OnOff Server   (responds to on/off)
            - Light Lightness Server (responds to brightness)
            - Health Server          (reports faults)
```

Key concepts:

- **Node**: a provisioned device in the network. Has a unicast address.
- **Element**: an addressable entity within a node. A multi-gang switch has multiple elements (one per gang).
- **Model**: defines behavior — a "Generic OnOff Server" handles on/off; a "Generic OnOff Client" sends on/off. SIG-defined models (standard) or vendor models (custom).
- **Address types**:
  - **Unicast**: one element.
  - **Group**: a set of elements ("all kitchen lights").
  - **Virtual**: a label-hashed group.
- **Publish/Subscribe**: a model *publishes* messages to an address; models *subscribed* to that address receive them. A wall switch publishes "OnOff=0" to group "kitchen"; all kitchen lights subscribe to "kitchen" and turn off.
- **Relay**: nodes with the relay feature re-broadcast messages, extending range. This flooding is how a message reaches across a building.

### Security

Mesh has two key tiers:
- **Network key (NetKey)**: shared by all nodes in the network; encrypts at the network layer (relay nodes can relay without decrypting the application payload).
- **Application key (AppKey)**: per-application; encrypts the payload. A light and a switch share an AppKey; relay nodes don't have it.

This two-tier scheme lets relays forward traffic they can't read — important for security at scale.

## 97.3  Provisioning — adding a node to the network

A fresh node is **unprovisioned** — it advertises "I want to join." A **provisioner** (a phone app, or your i.MX6ULL) runs the provisioning protocol:

```
1. Unprovisioned node beacons.
2. Provisioner discovers it, initiates provisioning.
3. ECDH key exchange (the node and provisioner derive a shared secret).
4. (Optional) Out-of-band authentication (a number to confirm, a QR code).
5. Provisioner assigns: unicast address, NetKey, an IV index.
6. Node is now provisioned — part of the network.
7. Provisioner (or a Configuration Client) binds AppKeys to the node's models
   and sets up publish/subscribe.
```

Provisioning is the security-critical step — it's where keys are distributed. The OOB authentication prevents a rogue provisioner from hijacking nodes.

## 97.4  bluez-mesh on Linux

Linux's BLE Mesh stack is **bluez-mesh** — a separate daemon (`bluetooth-meshd`) from the main `bluetoothd`, with its own D-Bus API. It uses the same HCI controller (Ch 95) but runs the mesh protocol stack.

```
   Applications (your mesh node logic, mesh-cfgclient)
        │ D-Bus (org.bluez.mesh)
        ▼
   bluetooth-meshd (the mesh daemon)
        │ HCI sockets
        ▼
   Kernel BT subsystem
        │ HCI
        ▼
   Controller (must support BLE advertising + scanning)
```

The controller needs to support BLE advertising + scanning (any BLE 4.0+ controller does — nRF52, BCM4343, a USB dongle).

Start the daemon:

```
[root@pa-mini:~]# bluetooth-meshd --config /var/lib/bluetooth/mesh &
```

Tools:
- **`mesh-cfgclient`**: a provisioner + configuration client (provision nodes, bind keys, set pub/sub).
- **`meshctl`**: older combined tool.

## 97.5  A worked example — the i.MX6ULL as a mesh provisioner + gateway

Scenario: 5 smart lights (each a small nRF52 node running a "Generic OnOff Server"), and the i.MX6ULL as the provisioner + gateway (bridging the mesh to MQTT/cloud, so a cloud command controls the lights).

### Step 1: create the network (on the i.MX6ULL)

```
[root@pa-mini:~]# mesh-cfgclient
[mesh-cfgclient]# create          ← create a new network (generates NetKey)
Created mesh network with token ...
[mesh-cfgclient]# appkey-create 0 0   ← create an AppKey, bound to NetKey 0
```

### Step 2: provision each light

```
[mesh-cfgclient]# discover-unprovisioned on   ← scan for unprovisioned nodes
Scan result: device UUID aabbcc...
[mesh-cfgclient]# provision aabbcc...           ← provision this node
Assigning address 0x0002
Provisioning done
```

Repeat for each light (addresses 0x0002, 0x0003, ...).

### Step 3: bind the AppKey + configure pub/sub

```
[mesh-cfgclient]# menu config
[config]# target 0002                          ← configure node at 0x0002
[config]# appkey-add 0                          ← give it AppKey 0
[config]# bind 0 0 1000                          ← bind AppKey 0 to the OnOff model (0x1000)
[config]# sub-add 0002 c000 1000                 ← subscribe its OnOff model to group 0xC000 ("all lights")
```

Now node 0x0002's OnOff model has the AppKey and is subscribed to group 0xC000.

### Step 4: control the lights

```
[mesh-cfgclient]# menu onoff
[onoff]# target c000        ← address the "all lights" group
[onoff]# onoff 1            ← turn all subscribed lights ON
[onoff]# onoff 0            ← turn them all OFF
```

One message to group 0xC000 → all 5 lights respond. Add more lights, subscribe them to 0xC000, and they join the group automatically — no reconfiguration of the others. Group addressing is what makes this possible.

### Step 5: bridge to MQTT (the gateway role)

Your i.MX6ULL app, via the `org.bluez.mesh` D-Bus API, subscribes to mesh status messages and publishes commands. Wire it to an MQTT client:

```python
# Conceptual gateway loop
on_mqtt("home/lights/kitchen/set", lambda payload:
    mesh_publish(group=0xC000, model="OnOff", value=int(payload)))
on_mesh_status(lambda node, value:
    mqtt_publish(f"home/lights/{node}/state", value))
```

Now a cloud/phone MQTT command controls the mesh lights, and light state changes propagate to the cloud. The i.MX6ULL is the **mesh-to-IP gateway** — the typical role for a Linux device in a mesh network (the lights are cheap nRF52 nodes; the gateway is the one Linux box).

## 97.6  Building a mesh node application

For the i.MX6ULL to be a *node* (not just a provisioner) — e.g., a mesh sensor that publishes temperature — you write an application against `org.bluez.mesh`'s `Application1` + `Element1` interfaces, declaring your models and handling incoming messages. BlueZ ships `test/test-mesh` as a starting point. The structure: declare elements + models, register with `bluetooth-meshd`, implement the model message handlers (`DevKeyMessageReceived`, `MessageReceived`).

The structure is similar to the GATT server of Ch 95 but applies to mesh models. It is more involved, and the bluez-mesh D-Bus API is less mature than the GATT one. For most products, the i.MX6ULL is the *provisioner/gateway* (using `mesh-cfgclient`), and the cheap nodes (nRF52 with Zephyr/nRF SDK mesh firmware) are the *servers*.

## 97.7  Lab

1. **Start bluetooth-meshd.** Verify it runs with your HCI controller (Ch 95).
2. **Create a network.** `mesh-cfgclient` → `create`. Note the NetKey + token.
3. **Provision a node.** Use an nRF52 dev kit flashed with a mesh "light" sample (Nordic SDK or Zephyr). Discover + provision it.
4. **Bind + subscribe.** Give it AppKey 0; bind to the OnOff model; subscribe to a group.
5. **Control it.** Send OnOff to the group; the light responds.
6. **Multi-node.** Provision 3+ nodes into the same group. One command controls all.
7. **Relay test.** Place a node out of direct range of the i.MX6ULL but within range of another node. Verify the message relays (the far node still responds). This is the mesh magic.
8. **MQTT gateway.** Bridge a mesh group to MQTT; control the lights from an MQTT client (mosquitto_pub).

## 97.8  Pitfalls

- **bluetooth-meshd vs bluetoothd.** They're separate daemons and can conflict over the HCI controller. Run mesh on a dedicated controller, or ensure only one daemon claims `hci0`.
- **Provisioning OOB confusion.** If OOB authentication is configured, both sides must agree on the method (number, QR, none). Mismatch = provisioning fails.
- **AppKey not bound.** A provisioned node that hasn't had an AppKey bound to its model can't decrypt application messages — it joins the network but ignores commands. Always bind the AppKey.
- **Forgetting subscription.** A node bound to an AppKey but not subscribed to the target group won't receive group messages. Both bind *and* subscribe.
- **Relay feature off.** If no nodes relay, range is limited to one hop. Enable relay on enough nodes for coverage (but not *all* — too many relays cause message storms).
- **IV index / replay protection drift.** Mesh uses sequence numbers as replay protection. If a node's stored sequence state is lost (because its flash was erased), the network may reject it. Persist mesh state correctly.
- **bluez-mesh maturity.** The Linux mesh stack and D-Bus API are less polished than GATT. Expect rough edges; commercial mesh systems often use vendor stacks (Silicon Labs, Nordic) on the nodes and a custom gateway.
- **Provisioning capacity.** A network has a finite address space and key storage. Plan addressing (unicast ranges, group allocation) before deploying hundreds of nodes.

## 97.9  Going deeper

- **`bluetooth-meshd` + `mesh-cfgclient`** (BlueZ) — the Linux mesh daemon + provisioner tool.
- **BlueZ `test/test-mesh`** — a sample mesh node application.
- **BlueZ `doc/mesh-api.txt`** — the `org.bluez.mesh` D-Bus API.
- **Bluetooth Mesh Profile Specification** + **Mesh Model Specification** (Bluetooth SIG) — the canonical references.
- **Nordic nRF5 SDK for Mesh / Zephyr Bluetooth Mesh** — for the *node* firmware (the cheap nRF52 lights).
- **Silicon Labs Bluetooth Mesh docs** — an alternative node stack with good tutorials.
- **Ch 95** — the underlying HCI controller bring-up that mesh sits on.

---

> **End of Group L — Bluetooth (Ch 95–97).** Full HCI + BlueZ GATT (Ch 95, the capable path), AT-command transparent-serial BLE (Ch 96, the simple path), and BLE Mesh (Ch 97, the building-scale path). The i.MX6ULL spans roles from a single BLE sensor to a mesh gateway.

> Next chapter: **Chapter 98 — LoRa.** Group M (Long-range & specialty wireless) — kilometre-range sub-GHz radio with the SX127x/SX126x, LoRaWAN vs point-to-point, and the spreading-factor trade-offs.
