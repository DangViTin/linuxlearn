---
chapter: 27A
title: DT bindings YAML and dt_binding_check
part: IV — The Kernel (supplementary v1.2)
estimated_pages: 14
status: draft
---

# Chapter 27A — DT bindings YAML and `dt_binding_check`

> **What:** the mainline kernel's machine-checkable description of every Device Tree binding — a JSON-Schema document (in YAML form) that says *exactly* which properties a node should have, of what type, with what constraints. Plus the `make dt_binding_check` / `make dtbs_check` targets that validate your DTS against them.
> **Why:** Since kernel v4.18 (mid-2018), every new binding *must* ship a YAML schema, and existing bindings are being migrated. Without a schema, your patch will not be accepted upstream. Without a schema check on your CI, your binding can silently drift between board variants and you'll only discover it when something breaks.
> **Focus:** the **schema as a contract**. A binding YAML is the source of truth for what a node *should* look like. The DTS files are checked against it; drivers are documented by it. Master one binding YAML and you can read or write any of them.

## 27A.1  Why bindings need schemas

For the first ~15 years of Device Tree's life, "bindings" lived as free-form `.txt` files in `Documentation/devicetree/bindings/`. A typical pre-2018 binding looked like:

```
* Freescale i.MX UART

Required properties:
- compatible: should be "fsl,<soc>-uart"
- reg: address and length of the register region
- interrupts: should contain the UART interrupt

Optional properties:
- fsl,dte-mode: indicates the UART is in DTE mode
```

Two problems:

1. **Not machine-checkable.** A DTS file with a typo (`compatible = "fsl,imx6ull-art";` — missing the `u`) or with a missing property silently passes compilation. Kernel just doesn't probe the device at runtime, and you go hunting.
2. **Inconsistent.** Two binding files written by two people, even for closely-related hardware, would describe things in subtly different ways. Some used `reg` for one purpose, some another. No way to enforce style.

Since 2018, every new binding ships as a **YAML file containing a JSON-Schema**. Schemas are validated automatically; DTS files are linted against them; CI rejects bindings that fail the lint. The `.txt` bindings are being migrated, with a deadline that keeps slipping but is real: any *new* binding without YAML is rejected.

## 27A.2  Anatomy of a binding YAML

Open `Documentation/devicetree/bindings/serial/fsl-imx-uart.yaml` (the i.MX UART binding). Lightly elided:

```yaml
# SPDX-License-Identifier: (GPL-2.0-only OR BSD-2-Clause)
%YAML 1.2
---
$id: http://devicetree.org/schemas/serial/fsl-imx-uart.yaml#
$schema: http://devicetree.org/meta-schemas/core.yaml#

title: Freescale i.MX Universal Asynchronous Receiver/Transmitter (UART)

maintainers:
  - Fabio Estevam <festevam@gmail.com>

allOf:
  - $ref: serial.yaml#

properties:
  compatible:
    oneOf:
      - enum:
          - fsl,imx1-uart
          - fsl,imx21-uart
      - items:
          - enum:
              - fsl,imx25-uart
              - fsl,imx27-uart
              - fsl,imx31-uart
              - fsl,imx35-uart
              - fsl,imx50-uart
              - fsl,imx51-uart
              - fsl,imx53-uart
              - fsl,imx6q-uart
          - const: fsl,imx21-uart
      - items:
          - enum:
              - fsl,imx6sl-uart
              - fsl,imx6sll-uart
              - fsl,imx6ul-uart
          - const: fsl,imx6q-uart
          - const: fsl,imx21-uart

  reg:
    maxItems: 1

  interrupts:
    maxItems: 1

  clocks:
    items:
      - description: IPG clock for the UART
      - description: Per-module clock for the UART

  clock-names:
    items:
      - const: ipg
      - const: per

  dmas:
    items:
      - description: DMA channel for RX
      - description: DMA channel for TX

  dma-names:
    items:
      - const: rx
      - const: tx

  fsl,uart-has-rtscts:
    type: boolean
    description: |
      Indicates the UART has RTS and CTS lines, that are mostly required to do
      hardware flow control. Deprecated, use uart-has-rtscts instead.

  uart-has-rtscts: true

  fsl,dte-mode:
    type: boolean
    description: |
      Indicate the uart works in DTE mode. The uart works in DCE mode by default.

required:
  - compatible
  - reg
  - interrupts
  - clocks
  - clock-names

unevaluatedProperties: false

examples:
  - |
    #include <dt-bindings/clock/imx6sx-clock.h>
    aliases {
        serial0 = &uart1;
    };

    uart1: serial@2020000 {
        compatible = "fsl,imx6sx-uart", "fsl,imx21-uart";
        reg = <0x02020000 0x4000>;
        interrupts = <GIC_SPI 26 IRQ_TYPE_LEVEL_HIGH>;
        clocks = <&clks IMX6SX_CLK_UART_IPG>,
                 <&clks IMX6SX_CLK_UART_SERIAL>;
        clock-names = "ipg", "per";
        uart-has-rtscts;
        fsl,dte-mode;
    };
```

Section-by-section:

- **`$id`** — globally unique URL for this schema. Used by `$ref` to pull schemas in from other files.
- **`title`** — human-readable. Shows up in generated docs.
- **`maintainers`** — who signs off on changes.
- **`allOf: [$ref: serial.yaml#]`** — inherits constraints from a parent schema. Every UART binding includes the generic-serial schema, which adds e.g. `current-speed` and `rs485-*` properties.
- **`properties`** — the meat. Each property gets a sub-schema saying what kind of value it accepts.
  - `compatible.oneOf` — three legal forms. (a) Just `fsl,imx1-uart` or `fsl,imx21-uart` alone. (b) `fsl,imx25-uart` (or one of several others) followed by a fallback to `fsl,imx21-uart`. (c) A three-string list ending in `fsl,imx21-uart`. Anything else is rejected.
  - `reg.maxItems: 1` — exactly one address-range, no more.
  - `clocks.items` — exactly two entries; the schema even documents what each represents.
  - `clock-names.items` — must be the literal strings "ipg" and "per", in that order.
  - `uart-has-rtscts: true` — equivalent to "this is a boolean flag" (the value `true` after a name is the YAML shorthand for "this is a valid property with no additional constraints").
- **`required`** — properties that MUST be present.
- **`unevaluatedProperties: false`** — *no other properties* are allowed. This catches typos. If you wrote `clock-name` (singular), the schema rejects it as an unknown property.
- **`examples`** — a working DT fragment that must validate against the schema. Doubly useful: it documents usage *and* it's lint-checked as part of `dtbs_check`.

This single file replaces what used to be ~30 lines of free-form English, and it's machine-verifiable.

## 27A.3  Running the checks

Two `make` targets:

```sh
$ make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- dt_binding_check
$ make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- dtbs_check
```

What each does:

- **`dt_binding_check`** validates every binding YAML file *against the meta-schema*. Catches errors *in the bindings themselves*: malformed YAML, references to non-existent parent schemas, missing required meta-fields. Run this when you write or edit a binding.
- **`dtbs_check`** compiles every DTS for the current arch, then validates each *compiled DTB* against the matching binding schema. Catches errors *in the DT source*: wrong property types, missing required properties, extra unknown properties. Run this when you edit a DTS.

Prerequisites:

```sh
$ pip install --user --upgrade dtschema yamllint
```

`dtschema` is the validator that does the actual matching. `yamllint` catches YAML formatting issues.

A typical `dtbs_check` run on the i.MX tree produces ~100 warnings as of v6.6 — many existing DTS files have minor issues that haven't been cleaned up. New code should add *zero* new warnings; the upstream maintainers will require that.

## 27A.4  Writing your first binding

Suppose your custom board has a GPIO-driven LED that you want to teach the kernel about cleanly. (The existing `gpio-leds` binding handles this; we'll author a fictional "my-pa-led" binding for pedagogy, then in practice you'd use `gpio-leds` instead.)

`Documentation/devicetree/bindings/leds/myorg,pa-led.yaml`:

```yaml
# SPDX-License-Identifier: (GPL-2.0-only OR BSD-2-Clause)
%YAML 1.2
---
$id: http://devicetree.org/schemas/leds/myorg,pa-led.yaml#
$schema: http://devicetree.org/meta-schemas/core.yaml#

title: My-Org Point Atom LED

maintainers:
  - Your Name <you@example.org>

description: |
  A single GPIO-driven LED on the Point Atom MINI / ALPHA boards.
  Active-low (cathode connected to the GPIO; anode through resistor to 3V3).

properties:
  compatible:
    const: myorg,pa-led

  gpios:
    maxItems: 1
    description: GPIO connected to the LED's cathode

  default-state:
    enum: [on, off, keep]
    default: off

required:
  - compatible
  - gpios

additionalProperties: false

examples:
  - |
    #include <dt-bindings/gpio/gpio.h>

    led0 {
        compatible = "myorg,pa-led";
        gpios = <&gpio1 3 GPIO_ACTIVE_LOW>;
        default-state = "off";
    };
```

Save that and run:

```sh
$ make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- dt_binding_check \
    DT_SCHEMA_FILES=leds/myorg,pa-led.yaml
```

If the schema is well-formed, the example inside it compiles cleanly and the binding-check passes. If you have a typo, you'll get a precise error pointing at the line.

Then, to add the matching DT node to a board:

```dts
/ {
    led0 {
        compatible = "myorg,pa-led";
        gpios = <&gpio1 3 GPIO_ACTIVE_LOW>;
        default-state = "off";
    };
};
```

And `make ARCH=arm dtbs_check` validates that against the schema you just wrote.

## 27A.5  Common schema patterns

A short library of patterns you'll re-use:

### Property whose value is one of a fixed set

```yaml
my-mode:
  enum: [polled, irq, dma]
  default: polled
```

### Property whose value is a number in a range

```yaml
my-freq-hz:
  $ref: /schemas/types.yaml#/definitions/uint32
  minimum: 1000000
  maximum: 50000000
```

### Property whose value is a string matching a pattern

```yaml
label:
  pattern: '^[a-z0-9-]+$'
```

### Property whose value depends on `compatible`

```yaml
allOf:
  - if:
      properties:
        compatible:
          contains:
            const: myorg,pa-board-rev-b
    then:
      required:
        - my-rev-b-only-property
```

### A pair of related arrays whose lengths must match

```yaml
foo:
  $ref: /schemas/types.yaml#/definitions/uint32-array
  minItems: 1
  maxItems: 8

foo-names:
  minItems: 1
  maxItems: 8

# Then in the example, foo and foo-names have the same number of items.
```

Most real bindings use 5-10 patterns from this library. Reading existing bindings in `Documentation/devicetree/bindings/` is the fastest way to learn them.

## 27A.6  Inheriting from base schemas

A binding rarely starts from scratch. Almost every binding `allOf:`-includes one or more parents:

- **`serial.yaml`** for UARTs
- **`i2c-controller.yaml`** for I²C buses
- **`spi-controller.yaml`** for SPI buses
- **`leds.yaml`** for LED-class devices
- **`hwmon.yaml`** for hardware monitoring

These parents define standard properties common to the *class* (e.g., `current-speed` for serial, `clock-frequency` for I²C buses). Inheriting from them means your binding picks up that vocabulary automatically and is validated consistently with everyone else's.

## 27A.7  Lab

1. **Run the checks.** From your kernel tree: `make ARCH=arm dt_binding_check` and `make ARCH=arm dtbs_check`. Note how many warnings the v6.6 tree produces. Don't try to fix them; just observe.
2. **Read a binding end-to-end.** Pick `Documentation/devicetree/bindings/serial/fsl-imx-uart.yaml`. Identify (a) the schema URL, (b) the parent schema, (c) which properties are required, (d) which are optional, (e) the example DT fragment.
3. **Find an unschema'd binding.** Look in `Documentation/devicetree/bindings/serial/` for any remaining `.txt` files. These are migration candidates. The `.txt` content is what needs to be turned into a `.yaml`.
4. **Write your first schema.** Pick a small driver (e.g., one of your own from Chapter 41 onward). Write its YAML. Run `dt_binding_check`. Cycle until clean.
5. **Break a passing DTS on purpose.** Edit `imx6ull-14x14-evk.dts` to misspell a property (`clock-name` instead of `clock-names`). Run `make dtbs_check`. Observe the precise error message that pinpoints the typo. Restore.
6. **Read `dtschema`'s source.** It's a small Python package; the dispatch from YAML schemas to JSON-Schema validation is in `dtschema/schemas/`.

## 27A.8  Pitfalls

- **Schema-validation passes but DT still doesn't work at runtime.** The schema only catches *syntactic* errors — wrong types, wrong arity, missing required props. Semantic errors (a `reg` value pointing at the wrong physical address) pass schema but fail at boot. Schema is necessary, not sufficient.
- **Forgetting to install `dtschema`.** Symptom: `dt_binding_check` reports zero warnings on a tree that clearly has issues. Means the validator silently isn't running. Verify: `pip show dtschema`.
- **Schema example doesn't validate.** Common when you write a binding without testing the example. Run `dt_binding_check` against your own binding *first*; only then propose it upstream.
- **`additionalProperties: false` too strict.** If you forget that the inherited base schema allows certain extra properties, the strict-mode rejection of "unknown" properties will reject legal usage. Use `unevaluatedProperties: false` (which respects `allOf` inheritance) instead.
- **`maxItems` vs `items`.** `maxItems: 1` says "up to one entry, of any type". `items: [- description: foo]` says "exactly one entry, described as foo". Different. Use the latter when you want to document semantics.

## 27A.9  Going deeper

- **`Documentation/devicetree/writing-schema.rst`** — the canonical tutorial.
- **`Documentation/devicetree/bindings/example-schema.yaml`** — a fully-annotated example schema. Read it after this chapter.
- **`dtschema` source** — `github.com/devicetree-org/dt-schema`. Read for ground truth on what's actually validated.
- **JSON Schema spec** at `json-schema.org/specification`. DT bindings use JSON Schema vocabulary; this is the underlying spec.
- **`grep -r "unevaluatedProperties" Documentation/devicetree/bindings/`** — read a few real-world bindings end-to-end before writing your own.

> Next chapter: **Chapter 28 — Kernel startup, traced.** With DT understood, we can now trace `start_kernel()` from its first instruction to the moment it `exec`s `/sbin/init`.
