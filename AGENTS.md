# Working on the Orca reference

Keep the common EC2, networking, access, storage and Orca layers independent of the selected coding agent. Put provider-specific IAM and configuration in the agent module.

Run the offline suite and render a template before changing deployment defaults. Validate infrastructure changes with CloudFormation. Use a fresh disposable stack for an explicitly requested end-to-end deployment. Record the test scope and clean up any retained test volumes and recovery points.

Never commit real inventories, pairing offers, authentication state, account-specific grants or device identifiers. Preserve the independent mobile-to-EC2 access path. Check existing work and make a recovery point before changing a live workstation's capacity or runtime.
