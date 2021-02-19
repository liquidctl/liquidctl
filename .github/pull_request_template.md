Describe what the changes are meant to address.

If the implementation is non trivial, please also include a short overview.

<!-- Tags (fill and keep as many as applicable): -->

Fixes: #number of issue (implies Closes tag) or commit SHA
Closes: #number of issue or pull request
Related: #number of issue/pull request, or link to external discussion

---

Checklist:

<!-- To check an item, fill the brackets with the letter x; the result should look like `[x]`.  Feel free to leave unchecked items that are not applicable or that you could not perform. -->

- [ ] Add automated tests cases
- [ ] Conform to the style guide in `docs/developer/style-guide.md`
- [ ] Verify that all automated tests pass
- [ ] Verify that the changes work as expected on real hardware
- [ ] [New CLI flag?] Adjust the completion scripts in `extra/completions/`
- [ ] [New device?] Regenerate `extra/linux/71-liquidctl.rules` (see file header)
- [ ] [New device?] Add entry to the README's supported device list with applicable notes (at least `EN`)
- [ ] [New driver?] Document the protocol in `docs/developer/protocol/`
- [ ] Update (or add) applicable `docs/*guide.md` device guides
- [ ] Update the `liquidctl.8` Linux/Unix/Mac OS man page
- [ ] Update the README and other applicable documentation pages
- [ ] Submit relevant device data to https://github.com/liquidctl/collected-device-data
