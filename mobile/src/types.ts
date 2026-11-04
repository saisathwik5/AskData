export interface Step {
  type: string;
  step?: number;
  tool?: string;
  arguments?: any;
  result?: any;
  rejection?: string;
  thought?: string;
  answer?: string;
  metrics?: {
    total_steps: number;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    estimated_cost_usd: number;
    guard_retries: number;
  };
}

export interface ChartSpec {
  type: string;
  chart_type: string;
  title: string;
  x_axis: string;
  y_axis: string;
  data: any[];
}

export interface Message {
  id: string;
  sender: "user" | "agent";
  text: string;
  steps: Step[];
  charts: ChartSpec[];
  metrics?: any;
  loading?: boolean;
}

export interface ColumnDef {
  name: string;
  type: string;
  description: string;
  sample?: string;
}

export interface TableViewDef {
  name: string;
  description: string;
  rowCount: string;
  columns: ColumnDef[];
}
