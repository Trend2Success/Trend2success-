import twilio from "twilio";

export interface SmsSender {
  send(to: string, body: string): Promise<void>;
}

export class TwilioSmsSender implements SmsSender {
  private client: ReturnType<typeof twilio>;
  private fromNumber: string;

  constructor(accountSid: string, authToken: string, fromNumber: string) {
    this.client = twilio(accountSid, authToken);
    this.fromNumber = fromNumber;
  }

  async send(to: string, body: string): Promise<void> {
    await this.client.messages.create({ to, from: this.fromNumber, body });
  }
}
