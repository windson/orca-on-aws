# Connect a desktop or phone

Orca listens on EC2 port 6768. The security group has zero inbound rules. On the host, the firewall accepts the loopback interface and individual Tailscale IPv4 clients that the operator enrolls. Use a private interactive terminal for pairing. A pairing link or QR grants access to the workstation. Check your Session Manager logging policy before displaying an offer in a shell that others can review.

## Tailscale for mobile and desktop

1. Use the SSM session from the quickstart. On **EC2**, join your tailnet and follow Tailscale's sign-in link. Choose a unique hostname for this workstation.

   ```sh
   sudo tailscale up --hostname=orca-dev
   tailscale ip -4
   ```

2. On the **phone or computer**, sign in to the same tailnet and turn the VPN on. Read the **client's own** Tailscale IPv4 address in its Tailscale app. If your tailnet uses access policies, allow this client to reach the workstation on TCP 6768.
3. Back on EC2, replace `CLIENT_TAILSCALE_IPV4` with that client address. Repeat once per device. The command persists the allowlist on the encrypted workspace.

   ```sh
   sudo /opt/orca-workstation/access/allow-client add CLIENT_TAILSCALE_IPV4
   ```

4. Generate the offer on EC2. Choose the command for your client. In **Orca Mobile**, open **Pair**, then scan the terminal QR or paste the pairing link. In **Orca Desktop**, open **Settings → Remote Orca Servers**, add the server and import the desktop offer. Select the remote host when opening your project.

   ```sh
   # Android
   sudo -iu orca orca-host pair --mobile --address "$(tailscale ip -4)"

   # Desktop on Tailscale
   sudo -iu orca orca-host pair --address "$(tailscale ip -4)"
   ```

5. Send a message from each client. On Android, keep Tailscale connected, switch Wi-Fi off, and send another message over mobile data with the laptop asleep. Both clients connect to EC2 independently.

## Desktop through Session Manager

If the desktop uses AWS credentials and Session Manager, it can use a local port forward. In a local terminal set `HOST_ID` from the stack output and keep this command running while that desktop is using Orca.

```sh
aws ssm start-session --profile default --region us-east-1 --target "$HOST_ID" \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["6768"],"localPortNumber":["16768"]}'
```

In a separate interactive EC2 session generate the desktop offer with `sudo -iu orca orca-host pair --address 127.0.0.1:16768`. Import the offer into the desktop client. The phone continues to use EC2's Tailscale address.

## Troubleshooting and removal

- **Direct WebSocket closed (1006)** means the socket ended without a normal close frame. Check that EC2 is running, the phone VPN is active on the current network, the phone's current Tailscale IPv4 is allowed, and the mobile offer advertises EC2's Tailscale address. A loopback offer points at the phone itself.
- **Host offline on both clients**. From SSM, run `sudo /opt/orca-workstation/verify`, `tailscale status`, and `sudo journalctl -u orca-server -u tailscaled --since '30 min ago'`. Check free space and kernel OOM events before restarting active work. For a desktop loopback connection, also check the forwarding process on that desktop.
- **Retire a client**. Revoke its Orca paired-device grant on the host and run `sudo /opt/orca-workstation/access/allow-client remove CLIENT_TAILSCALE_IPV4`. Remove a lost device from the tailnet. Removing a saved entry in the client only clears that copy.

[Orca remote servers](https://orca.dev/docs/remote-servers) · [Orca Mobile](https://orca.dev/docs/mobile) · [Tailscale access controls](https://tailscale.com/kb/1018/acls)
