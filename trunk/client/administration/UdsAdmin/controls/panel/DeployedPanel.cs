﻿//
// Copyright (c) 2012 Virtual Cable S.L.
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without modification, 
// are permitted provided that the following conditions are met:
//
//    * Redistributions of source code must retain the above copyright notice, 
//      this list of conditions and the following disclaimer.
//    * Redistributions in binary form must reproduce the above copyright notice, 
//      this list of conditions and the following disclaimer in the documentation 
//      and/or other materials provided with the distribution.
//    * Neither the name of Virtual Cable S.L. nor the names of its contributors 
//      may be used to endorse or promote products derived from this software 
//      without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
// DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE 
// FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
// DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
// SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
// CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
// OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

// author: Adolfo Gómez, dkmaster at dkmon dot com

using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Data;
using System.Linq;
using System.Text;
using System.Windows.Forms;

namespace UdsAdmin.controls.panel
{
    public partial class DeployedPanel : UserControl
    {
        private xmlrpc.DeployedService _parent;
        private bool _cache;
        ContextMenuStrip _deleteMenu;
        ContextMenuStrip _assignMenu;
        ContextMenuStrip _infoMenu;
        gui.ListViewSorter _listSorter;

        public DeployedPanel(xmlrpc.DeployedService parent, bool cache = false)
        {
            _parent = parent;
            _cache = cache;
            _deleteMenu = new ContextMenuStrip();
            _assignMenu = new ContextMenuStrip();
            _infoMenu = new ContextMenuStrip();
            InitializeComponent();

            ToolStripMenuItem delete = new ToolStripMenuItem(Strings.deleteItem); delete.Click += deleteItem; delete.Image = Images.delete16;
            _deleteMenu.Items.AddRange(new ToolStripItem[] { delete });

            ToolStripMenuItem info = new ToolStripMenuItem(Strings.errorInfo); info.Click += infoItem; info.Image = Images.find16;
            _infoMenu.Items.AddRange(new ToolStripItem[] { info });

            ToolStripMenuItem assign = new ToolStripMenuItem(Strings.assignToUser); assign.Click += assignToUser; assign.Image = Images.new16;
            _assignMenu.Items.AddRange(new ToolStripItem[] { assign });

            // Adapt listview to cache or users
            if (cache)
            {
                cacheHeaders();
            }
            else
            {
                assignedHeaders();
            }

            listView.ListViewItemSorter =  _listSorter = new gui.ListViewSorter(listView, new int[] { 3, 5 } );

            updateList();
        }

        private void DeployedPanel_VisibleChanged(object sender, EventArgs e)
        {
            if (Visible == true)
            {
                updateList();
            }
        }

        private void cacheHeaders()
        {
            ColumnHeader he = new ColumnHeader();
            he.Text = Strings.cacheLevel; he.TextAlign = HorizontalAlignment.Left; he.Width = 128;
            listView.Columns.Add(he);
        }

        private void assignedHeaders()
        {
            ColumnHeader userHeader = new ColumnHeader(); userHeader.Text = Strings.owner; userHeader.TextAlign = HorizontalAlignment.Center;
            ColumnHeader usedHeader = new ColumnHeader(); usedHeader.Text = Strings.occopied; usedHeader.TextAlign = HorizontalAlignment.Center;
            listView.Columns.AddRange(new ColumnHeader[]{ userHeader, usedHeader});
        }

        private ListViewItem getListViewItemFrom(xmlrpc.UserDeployedService uds)
        {
            if (_cache == true)
                return new ListViewItem(new string[] { uds.uniqueId, uds.friendlyName, uds.revision, uds.creationDate.ToString(), 
                    xmlrpc.Util.GetStringFromState(uds.state, uds.osState), uds.stateDate.ToString(), 
                             ((xmlrpc.CachedDeployedService)uds).cacheLevel});
            xmlrpc.AssignedDeployedService udss = (xmlrpc.AssignedDeployedService)uds;
            return new ListViewItem(new string[] { uds.uniqueId, uds.friendlyName, uds.revision, uds.creationDate.ToString(), 
                xmlrpc.Util.GetStringFromState(uds.state, uds.osState), uds.stateDate.ToString(), udss.user, udss.inUse ? Strings.yes : Strings.no} );
        }

        private void updateList()
        {

            xmlrpc.UserDeployedService[] servs;
            if (_cache == true)
                servs = xmlrpc.UdsAdminService.GetCachedDeployedServices(_parent);
            else
                servs = xmlrpc.UdsAdminService.GetAssignedDeployedServices(_parent);

            List<ListViewItem> lst = new List<ListViewItem>();
            foreach (xmlrpc.UserDeployedService uds in servs)
            {
                ListViewItem itm = getListViewItemFrom(uds);
                itm.Tag = uds.id;
                itm.ForeColor = gui.Colors.getColorForState(uds.state);
                lst.Add(itm);
            }
            listView.Items.Clear();
            listView.Items.AddRange(lst.ToArray());
        }

        private void assignToUser(object sender, EventArgs e)
        {
            UdsAdmin.forms.AssignDeployed form = new UdsAdmin.forms.AssignDeployed(_parent);
            if (form.ShowDialog() == DialogResult.OK)
                updateList();
        }

        private void infoItem(object sender, EventArgs e)
        {
            string id = (string)listView.SelectedItems[0].Tag;
            string error = xmlrpc.UdsAdminService.GetUserDeployedServiceError(id);
            MessageBox.Show(error, Strings.error, MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        private void deleteItem(object sender, EventArgs e)
        {
            if (listView.SelectedItems.Count == 0)
                return;
            string[] ids = new string[listView.SelectedItems.Count];
            int n = 0;
            foreach (ListViewItem i in listView.SelectedItems)
            {
                ids[n++] = (string)i.Tag;
            }
            try
            {
                xmlrpc.UdsAdminService.RemoveUserService(ids);
            }
            catch (CookComputing.XmlRpc.XmlRpcFaultException ex)
            {
                gui.UserNotifier.notifyRpcException(ex);
            }
            updateList();
        }

        private void listView_ColumnClick(object sender, ColumnClickEventArgs e)
        {
            _listSorter.ColumnClick(sender, e);
        }

        private void listView_MouseUp(object sender, MouseEventArgs e)
        {
            if (e.Button == System.Windows.Forms.MouseButtons.Right)
            {
                if (listView.SelectedItems.Count == 0)
                {
                    if (_parent.info.mustAssignManually)
                        _assignMenu.Show(Control.MousePosition.X, Control.MousePosition.Y);
                }
                else
                {
                    if (listView.SelectedItems.Count == 1 && listView.SelectedItems[0].SubItems[4].Text == xmlrpc.Util.GetStringFromState(xmlrpc.Constants.STATE_ERROR))
                        _infoMenu.Show(Control.MousePosition.X, Control.MousePosition.Y);
                    else
                        _deleteMenu.Show(Control.MousePosition.X, Control.MousePosition.Y);
                }
            }
        }

        private void listView_KeyUp(object sender, KeyEventArgs e)
        {
            switch (e.KeyCode)
            {
                case Keys.F5:
                    updateList();
                    break;
                case Keys.E:
                    if (e.Modifiers == Keys.Control)
                        foreach (ListViewItem i in listView.Items)
                            i.Selected = true;
                    break;
            }
        }

    }
}
