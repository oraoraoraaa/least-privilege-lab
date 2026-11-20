# Manuscript versions

Each row links to the TeX source and PDF as first committed on the research branch. Each folder includes the exact tables and figures its source loads. The commit link opens the full study and build files for that revision.

| Version | Manuscript | Revision | Files | Commit |
|---|---|---|---|---|
| 01 | When Does a Sibling Query Preserve Necessary Access? | Initial fixed-schema study of sibling queries | [PDF · 8 pages](v01-cf55c7d/paper.pdf) · [TeX](v01-cf55c7d/paper.tex) | [cf55c7d](https://github.com/oraoraoraaa/least-privilege-lab/commit/cf55c7df4bf8dbb030b11b4bafccd44d625fe1de) |
| 02 | When Does a Sibling Query Preserve Necessary Access? | Corrected labels in the study-design figure | [PDF · 8 pages](v02-458da4a/paper.pdf) · [TeX](v02-458da4a/paper.tex) | [458da4a](https://github.com/oraoraoraaa/least-privilege-lab/commit/458da4a53c8036002e701147d616ccbc7f3ecc5b) |
| 03 | When Does a Sibling Query Preserve Necessary Access? | Portable typesetting of the exact-counting formula | [PDF · 8 pages](v03-8be128e/paper.pdf) · [TeX](v03-8be128e/paper.tex) | [8be128e](https://github.com/oraoraoraaa/least-privilege-lab/commit/8be128e2cabc496762963d2c4eb664b05facaf11) |
| 04 | Which Preflight Preserves Query Access? | Migration preflight and shipped-query evidence | [PDF · 11 pages](v04-71a1915/paper.pdf) · [TeX](v04-71a1915/paper.tex) | [71a1915](https://github.com/oraoraoraaa/least-privilege-lab/commit/71a1915d59c4cd653aab06ba88e5460e45146c21) |
| 05 | Which Preflight Preserves Query Access? | Full-column coverage comparison | [PDF · 11 pages](v05-86c98e9/paper.pdf) · [TeX](v05-86c98e9/paper.tex) | [86c98e9](https://github.com/oraoraoraaa/least-privilege-lab/commit/86c98e9a1b69526c6ccfd0f12bb611eea044e294) |
| 06 | Which SQL Migrations Need Rehearsal? | Five-project evaluation and shared-account enforcement | [PDF · 5 pages](v06-3dff090/paper.pdf) · [TeX](v06-3dff090/paper.tex) | [3dff090](https://github.com/oraoraoraaa/least-privilege-lab/commit/3dff09051c257983fcbb2a709d0590f0e24b561a) |
| 07 | Which SQL Migrations Need Rehearsal? | Prospective selective-rehearsal test and recipient access | [PDF · 5 pages](v07-54d63dd/paper.pdf) · [TeX](v07-54d63dd/paper.tex) | [54d63dd](https://github.com/oraoraoraaa/least-privilege-lab/commit/54d63dd9048408b710e188b9afc885f05a41e91e) |

To rebuild a version, open its folder and run the following commands. Three pdfLaTeX passes resolve the cross-references for every archived version. The rebuilt PDF is written to `build/paper.pdf`.

```sh
mkdir -p build
for pass in 1 2 3; do
    pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build paper.tex || break
done
```
