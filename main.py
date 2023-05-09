#!/usr/bin/env python3

from pyteal import *
from algosdk import mnemonic, account
from algosdk.v2client import algod
from algosdk.encoding import base64
from algosdk.logic import get_application_address
from algosdk.transaction import *

mn = ""
token = "a" * 64
server = "http://127.0.0.1:4001"

def approval_program():
    return Seq(
        If(Txn.application_id()).Then(
            # Set axfer to the index of the next transaction in the group
            (axfer := ScratchVar(TealType.uint64)).store(Txn.group_index() + Int(1)),

            # Assert Axfer is Asset Transfer
            Assert(Gtxn[axfer.load()].type_enum() == TxnType.AssetTransfer),
            # Assert Axfer is Asset Transfer to App
            Assert(Gtxn[axfer.load()].asset_receiver() == Global.current_application_address()),

            # If not already opted-in, opt-in
            (opted_in := AssetHolding.balance(Global.current_application_address(), Gtxn[axfer.load()].xfer_asset())),
            If(Not(opted_in.hasValue())).Then(
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder().SetFields({
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: Gtxn[axfer.load()].xfer_asset(),
                    TxnField.asset_receiver: Global.current_application_address(),
                    TxnField.fee: Int(0),
                }),
                InnerTxnBuilder.Submit(),
            )
        ),
        Approve(),
    )

def clear_program():
    return Approve()

if __name__ == "__main__":

    # Create Account
    sk = mnemonic.to_private_key(mn)
    pk = account.address_from_private_key(sk)

    # Create Algod Client
    client = algod.AlgodClient(token, server)

    # Translate PyTeal to TEAL
    approval_teal = compileTeal(approval_program(), Mode.Application, version=9)
    clear_teal = compileTeal(clear_program(), Mode.Application, version=9)

    # Compile TEAL to AVM Bytecode
    approval_bin = base64.b64decode(client.compile(approval_teal)["result"])
    clear_bin = base64.b64decode(client.compile(clear_teal)["result"])

    # Deploy Application
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 1000
    deploy_txn = ApplicationCreateTxn(
        sender = pk,
        sp = sp,
        on_complete = OnComplete.NoOpOC,
        approval_program = approval_bin,
        clear_program = clear_bin,
        global_schema = StateSchema(num_uints=0, num_byte_slices=0),
        local_schema = StateSchema(num_uints=0, num_byte_slices=0),
    )
    print("Deploying Application... ", end="")
    txid = client.send_transaction(deploy_txn.sign(sk))
    res = wait_for_confirmation(client, txid)
    print("DONE")
    app_id = res["application-index"]
    app_addr = get_application_address(app_id)
    print("Application ID: ", app_id)
    print("Application Address: ", app_addr)

    # Fund Application Account
    print("Funding Application Account... ", end="")
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 1000
    pay_txn = PaymentTxn(
        sender = pk,
        sp = sp,
        receiver = app_addr,
        amt = 2000000,
    )
    txid = client.send_transaction(pay_txn.sign(sk))
    res = wait_for_confirmation(client, txid)
    print("DONE")

    # Create Asset
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 1000
    asset_txn = AssetConfigTxn(
        sender = pk,
        sp = sp,
        total = 10000,
        decimals = 2,
        asset_name = "Demo Asset",
        unit_name = "DA",
        default_frozen = False,
        # manager = pk,
        # reserve = pk,
        # freeze = pk,
        # clawback = pk,
        strict_empty_address_check = False,
    )
    print("Creating Asset... ", end="")
    txid = client.send_transaction(asset_txn.sign(sk))
    res = wait_for_confirmation(client, txid)
    print("DONE")
    asset_id = res["asset-index"]
    print("Asset ID: ", asset_id)

    # Create Grouped Transaction
    # [ appl | axfer ]
    # The application call will check the asset transfer txn
    # to see if it's opted in, if not it will opt-in despite
    # not having the foreign asset included in the call.
    # This demonstrates shared resources.
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 2000
    appl_txn = ApplicationNoOpTxn(
        sender = pk,
        sp = sp,
        index = app_id,
    )
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = 1000
    axfer_txn = AssetTransferTxn(
        sender = pk,
        sp = sp,
        index = asset_id,
        receiver = app_addr,
        amt = 100,
    )
    print("Sending Grouped Transactions... ", end="")
    assign_group_id([appl_txn, axfer_txn])
    signed_txn = [appl_txn.sign(sk), axfer_txn.sign(sk)]
    txid = client.send_transactions(signed_txn)
    res = wait_for_confirmation(client, txid)
    print("DONE")

    # Check Application Address
    print("Checking Application Address... ", end="")
    res = client.account_info(app_addr)
    print("DONE")

    # Display Balance and Assets
    print("Application Address: ", app_addr)
    print("Balance: ", res["amount"])
    for asset in res["assets"]:
        print(f"Asset: ", asset)

