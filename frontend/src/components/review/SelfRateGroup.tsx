import { Button, Tooltip } from "antd";

import type { ReviewResult } from "../../types/review";
import { selfRateOptions } from "./shared";

interface SelfRateGroupProps {
  disabled?: boolean;
  loading?: boolean;
  onSelect: (value: ReviewResult) => void;
}

export default function SelfRateGroup({ disabled = false, loading = false, onSelect }: SelfRateGroupProps) {
  return (
    <div className="review-rate-grid">
      {selfRateOptions.map((option) => (
        <Tooltip key={option.value} title={option.tooltip}>
          <Button
            size="large"
            type={option.buttonType ?? "default"}
            danger={option.danger}
            className={["review-rate-button", option.className].filter(Boolean).join(" ")}
            disabled={disabled}
            loading={loading}
            onClick={() => onSelect(option.value)}
          >
            {option.key}. {option.label}
          </Button>
        </Tooltip>
      ))}
    </div>
  );
}
