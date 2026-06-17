import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  inject,
  input,
  output,
} from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import type { CapabilityDescriptor, CapabilityField } from '@photofant/models';

@Component({
  selector: 'pf-caption-preset-form',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule],
  templateUrl: './caption-preset-form.html',
  styleUrl: './caption-preset-form.scss',
})
export class CaptionPresetForm implements OnInit {
  readonly capabilities = input.required<CapabilityDescriptor>();
  readonly initialConfig = input<Record<string, unknown>>({});
  readonly configChange = output<Record<string, unknown>>();

  private readonly fb = inject(FormBuilder);

  protected form!: FormGroup;

  ngOnInit(): void {
    const controls: Record<string, unknown> = {};
    const initial = this.initialConfig();
    for (const field of this.capabilities().fields) {
      controls[field.key] = [initial[field.key] ?? field.default];
    }
    this.form = this.fb.nonNullable.group(controls);

    this.form.valueChanges.subscribe((value: Record<string, unknown>) => {
      this.configChange.emit(value);
    });
  }

  protected getFields(): CapabilityField[] {
    return this.capabilities().fields;
  }

  protected getDropdownOptions(field: CapabilityField): Array<{ value: string; label: string }> {
    return field.options ?? [];
  }

  getConfig(): Record<string, unknown> {
    return this.form.value as Record<string, unknown>;
  }
}
