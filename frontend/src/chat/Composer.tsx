import { type FormEvent, type KeyboardEvent, useId } from "react";
import { ui } from "../i18n/text";

export const MAX_MESSAGE_LENGTH = 1000;

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled: boolean;
  inputRef?: React.Ref<HTMLTextAreaElement>;
}

export function Composer({ value, onChange, onSend, disabled, inputRef }: Props) {
  const id = useId();
  const canSend = !disabled && value.trim().length > 0;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (canSend) onSend();
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      if (canSend) onSend();
    }
  }

  return (
    <form className="composer" onSubmit={submit}>
      <label htmlFor={id} className="visually-hidden">
        {ui.composer.label}
      </label>
      <textarea
        id={id}
        ref={inputRef}
        rows={1}
        value={value}
        maxLength={MAX_MESSAGE_LENGTH}
        placeholder={ui.composer.placeholder}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
      />
      <button type="submit" className="button button--primary" disabled={!canSend}>
        {ui.composer.send}
      </button>
    </form>
  );
}
