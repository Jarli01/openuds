﻿namespace UdsAdmin.forms
{
    partial class DeployedGroupForm
    {
        /// <summary>
        /// Variable del diseñador requerida.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Limpiar los recursos que se estén utilizando.
        /// </summary>
        /// <param name="disposing">true si los recursos administrados se deben eliminar; false en caso contrario, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Código generado por el Diseñador de Windows Forms

        /// <summary>
        /// Método necesario para admitir el Diseñador. No se puede modificar
        /// el contenido del método con el editor de código.
        /// </summary>
        private void InitializeComponent()
        {
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(DeployedGroupForm));
            this.tableLayoutPanel2 = new System.Windows.Forms.TableLayoutPanel();
            this.accept = new System.Windows.Forms.Button();
            this.cancel = new System.Windows.Forms.Button();
            this.tableLayoutPanel1 = new System.Windows.Forms.TableLayoutPanel();
            this.groupLabel = new System.Windows.Forms.Label();
            this.label1 = new System.Windows.Forms.Label();
            this.groupCombo = new System.Windows.Forms.ComboBox();
            this.authCombo = new System.Windows.Forms.ComboBox();
            this.tableLayoutPanel2.SuspendLayout();
            this.tableLayoutPanel1.SuspendLayout();
            this.SuspendLayout();
            // 
            // tableLayoutPanel2
            // 
            resources.ApplyResources(this.tableLayoutPanel2, "tableLayoutPanel2");
            this.tableLayoutPanel2.Controls.Add(this.accept, 0, 0);
            this.tableLayoutPanel2.Controls.Add(this.cancel, 2, 0);
            this.tableLayoutPanel2.Name = "tableLayoutPanel2";
            // 
            // accept
            // 
            resources.ApplyResources(this.accept, "accept");
            this.accept.Name = "accept";
            this.accept.UseVisualStyleBackColor = true;
            this.accept.Click += new System.EventHandler(this.accept_Click);
            // 
            // cancel
            // 
            resources.ApplyResources(this.cancel, "cancel");
            this.cancel.DialogResult = System.Windows.Forms.DialogResult.Cancel;
            this.cancel.Name = "cancel";
            this.cancel.UseVisualStyleBackColor = true;
            // 
            // tableLayoutPanel1
            // 
            resources.ApplyResources(this.tableLayoutPanel1, "tableLayoutPanel1");
            this.tableLayoutPanel1.Controls.Add(this.groupLabel, 0, 1);
            this.tableLayoutPanel1.Controls.Add(this.label1, 0, 0);
            this.tableLayoutPanel1.Controls.Add(this.groupCombo, 1, 1);
            this.tableLayoutPanel1.Controls.Add(this.authCombo, 1, 0);
            this.tableLayoutPanel1.Name = "tableLayoutPanel1";
            // 
            // groupLabel
            // 
            resources.ApplyResources(this.groupLabel, "groupLabel");
            this.groupLabel.Name = "groupLabel";
            // 
            // label1
            // 
            resources.ApplyResources(this.label1, "label1");
            this.label1.Name = "label1";
            // 
            // groupCombo
            // 
            this.groupCombo.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.groupCombo.FormattingEnabled = true;
            resources.ApplyResources(this.groupCombo, "groupCombo");
            this.groupCombo.Name = "groupCombo";
            // 
            // authCombo
            // 
            this.authCombo.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.authCombo.FormattingEnabled = true;
            resources.ApplyResources(this.authCombo, "authCombo");
            this.authCombo.Name = "authCombo";
            this.authCombo.SelectedIndexChanged += new System.EventHandler(this.authCombo_SelectedIndexChanged);
            // 
            // DeployedGroupForm
            // 
            this.AcceptButton = this.accept;
            resources.ApplyResources(this, "$this");
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.CancelButton = this.cancel;
            this.Controls.Add(this.tableLayoutPanel1);
            this.Controls.Add(this.tableLayoutPanel2);
            this.Name = "DeployedGroupForm";
            this.Load += new System.EventHandler(this.DeployedGroupForm_Load);
            this.tableLayoutPanel2.ResumeLayout(false);
            this.tableLayoutPanel1.ResumeLayout(false);
            this.tableLayoutPanel1.PerformLayout();
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.TableLayoutPanel tableLayoutPanel2;
        private System.Windows.Forms.Button accept;
        private System.Windows.Forms.Button cancel;
        private System.Windows.Forms.TableLayoutPanel tableLayoutPanel1;
        private System.Windows.Forms.Label groupLabel;
        private System.Windows.Forms.ComboBox groupCombo;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.ComboBox authCombo;
    }
}