# Priority fixes

## P0: Fix before sharing publicly

- Replace Chapter 60/61/62/60A references with actual chapter numbers: 122, 123, 124, 122A.
- Update `book/index.md` status table; Part VII and VIII are not "Not yet drafted".
- Update or remove `book/status.md`; it currently contradicts the file tree.
- Explain the Chapter 56-63 gap or renumber Part VII.
- Rename `book/part7-debug` to `book/part8-debug`, or document the mismatch.
- Replace `Ch 47 §47.x` placeholders with exact section numbers.
- Remove the `TODO` in `ch14-ddr3-init.md` or mark the chapter as incomplete.

## P1: Improve reader trust

- Add per-chapter tested environment boxes.
- Convert `estimated_pages` to actual generated page count or planned page target.
- Add source citations for hardware/security claims: NXP reference manual chapter, U-Boot file, Linux file, binding path.
- Add "what can go wrong" tables to HAB, OP-TEE, OTA, field updates, and wireless chapters.
- For every "from scratch driver" chapter, state whether the code is complete, partial, pseudo-code, or intentionally simplified.

## P2: Wording polish

- Reduce repeated "magic" phrasing. It works early, then becomes overused.
- Replace "just works" with the exact mechanism or conditions.
- Avoid jokes in safety/security chapters: "masochist", "cruel", "imposter" can stay in informal sidebars, not headings.
- Use consistent spelling: "artifact" vs "artefact", "customisation" vs "customization".

## P3: Structure improvements

- Add a dependency graph image or table after Chapter 1.
- Add a glossary appendix with acronyms: IVT, DCD, SPL, FIT, DTB, DTSI, VFS, IIO, ASoC, DAPM, HAB, SRK, CSF, RAUC.
- Add a "use existing driver vs write driver" decision table before Part VII.
- Add a "lab artifacts index": what files the reader should have after each chapter.
