import { Context } from 'hono';

export class HealthController {
  static async getRoot(c: Context) {
    return c.json({
      success: true,
      message: 'HPM Registry - Online Package Repository Server',
      version: '0.1.0',
      timestamp: new Date().toISOString(),
    });
  }

  static async getHealth(c: Context) {
    return c.json({
      success: true,
      status: 'healthy',
      service: 'hpm-registry',
      version: '0.1.0',
      timestamp: new Date().toISOString(),
    });
  }
}