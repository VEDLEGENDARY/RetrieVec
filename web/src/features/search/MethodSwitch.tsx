import { RadioGroup } from "../../ui";
import { MethodMark } from "./MethodMark";
import { methods, methodNames, methodDetails, type Method } from "./types";
export function MethodSwitch({
  value,
  onChange,
  structured,
}: {
  value: Method;
  onChange: (method: Method) => void;
  structured: boolean;
}) {
  return (
    <RadioGroup
      legend="Retrieval method"
      value={value}
      onChange={(next) => onChange(next as Method)}
      options={methods.map((method) => ({
        value: method,
        accessibleLabel: methodNames[method],
        disabled: structured && method !== "sparse",
        label: (
          <>
            <MethodMark method={method} />
            <span>
              {methodNames[method]}
              <small>{methodDetails[method]}</small>
            </span>
          </>
        ),
      }))}
    />
  );
}
