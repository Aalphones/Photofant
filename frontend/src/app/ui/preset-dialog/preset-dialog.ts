import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  ViewChild,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { FormBuilder, FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import type { CaptionPresetDto, CapabilityDescriptor } from '@photofant/models';
import { CaptionPresetForm } from '../caption-preset-form/caption-preset-form';
import { Icon } from '../icon/icon';

export interface PresetSavePayload {
  name: string;
  config: Record<string, unknown>;
  isDefault: boolean;
}

interface MetaFormControls {
  name: FormControl<string>;
  isDefault: FormControl<boolean>;
}

@Component({
  selector: 'pf-preset-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, CaptionPresetForm, Icon],
  templateUrl: './preset-dialog.html',
  styleUrl: './preset-dialog.scss',
})
export class PresetDialog implements OnInit {
  readonly capabilities = input.required<CapabilityDescriptor>();
  readonly preset = input<CaptionPresetDto | null>(null);
  readonly save = output<PresetSavePayload>();
  readonly cancel = output<void>();

  @ViewChild(CaptionPresetForm) private presetForm?: CaptionPresetForm;

  private readonly fb = inject(FormBuilder);

  protected metaForm!: FormGroup<MetaFormControls>;
  protected presetConfig = signal<Record<string, unknown>>({});

  ngOnInit(): void {
    const existing = this.preset();
    this.metaForm = this.fb.nonNullable.group<MetaFormControls>({
      name: this.fb.nonNullable.control(existing?.name ?? '', Validators.required),
      isDefault: this.fb.nonNullable.control(existing?.is_default ?? false),
    });
    if (existing != null) {
      this.presetConfig.set(existing.config);
    }
  }

  protected get isEditMode(): boolean {
    return this.preset() != null;
  }

  protected onConfigChange(config: Record<string, unknown>): void {
    this.presetConfig.set(config);
  }

  protected handleSave(): void {
    if (this.metaForm.invalid) { return; }
    const config = this.presetForm?.getConfig() ?? this.presetConfig();
    this.save.emit({
      name: this.metaForm.controls.name.value,
      config,
      isDefault: this.metaForm.controls.isDefault.value,
    });
  }

  protected handleCancel(): void {
    this.cancel.emit();
  }

  protected handleScrimClick(): void {
    this.cancel.emit();
  }
}
