import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { Icon } from '../../ui/icon/icon';

@Component({
  selector: 'pf-unlock',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, Icon],
  templateUrl: './unlock.html',
  styleUrl: './unlock.scss',
})
export class Unlock {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);

  readonly form = this.fb.nonNullable.group({
    password: ['', Validators.required],
  });

  protected readonly isLoading = signal(false);
  protected readonly hasError = signal(false);

  protected submit(): void {
    if (this.form.invalid || this.isLoading()) {
      return;
    }
    this.isLoading.set(true);
    this.hasError.set(false);

    this.auth.tryUnlock(this.form.controls.password.value).subscribe({
      next: (success: boolean) => {
        this.isLoading.set(false);
        if (success) {
          this.router.navigate(['/']);
        } else {
          this.hasError.set(true);
          this.form.controls.password.setValue('');
        }
      },
      error: () => {
        this.isLoading.set(false);
        this.hasError.set(true);
      },
    });
  }
}
