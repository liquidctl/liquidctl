Describe what the changes are meant to address.

If the implementation is not trivial, please also include a short overview.

<!-- Tags (fill in and keep as many as applicable): -->

Fixes: <!-- #number of issue (implies Closes tag) or commit SHA -->
Closes: <!-- #number of issue or pull request -->
Related: <!-- #number of issue/pull request, or link to external discussion -->

---

Checklist:

<!-- To check an item, fill the brackets with the letter x; the result should look like `[x]`.  Feel free to leave unchecked items that are not applicable or that you could not perform. -->

- [ ] Adhere to the [development process]
- [ ] Conform to the [style guide]
- [ ] Verify that the changes work as expected on real hardware
- [ ] Add automated tests cases
- [ ] Verify that all (other) automated tests (still) pass
- [ ] Update/add documentation
    - [ ] README, with ["new/changed in" notes]
    - [ ] applicable `docs/*guide.md` device guides, with ["new/changed in" notes]
    - [ ] `liquidctl.8` Linux/Unix/Mac OS man page
    - [ ] protocol documentation in `docs/developer/protocol`
- [ ] Submit relevant data, scripts or dissectors to https://github.com/liquidctl/collected-device-data

New CLI flag?

- [ ] Adjust the completion scripts in `extra/completions/`

New device?

- [ ] Regenerate `extra/linux/71-liquidctl.rules` (instructions in the file header)
- [ ] Add entry to the README's supported device list with applicable notes and `git` MRLV

New driver?

- [ ] Document the protocol in `docs/developer/protocol/`

[development process]: https://github.com/liquidctl/liquidctl/blob/main/docs/developer/process.md
[style guide]: https://github.com/liquidctl/liquidctl/blob/main/docs/developer/style-guide.md
["new/changed in" notes]: https://github.com/liquidctl/liquidctl/blob/main/docs/developer/process.md#newchanged-in-notes
